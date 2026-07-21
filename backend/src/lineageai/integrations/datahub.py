import time
from typing import Any

from datahub.emitter.mce_builder import (
    dataset_urn_to_key,
    make_dataset_urn,
    make_tag_urn,
)
from datahub.emitter.mcp import MetadataChangeProposalWrapper
from datahub.emitter.rest_emitter import DatahubRestEmitter
from datahub.ingestion.graph.client import DataHubGraph
from datahub.ingestion.graph.config import DatahubClientConfig
from datahub.metadata.schema_classes import (
    AuditStampClass,
    DatasetLineageTypeClass,
    DatasetProfileClass,
    DatasetPropertiesClass,
    GlobalTagsClass,
    SchemaMetadataClass,
    TagAssociationClass,
    UpstreamClass,
    UpstreamLineageClass,
)

from lineageai.config import Settings
from lineageai.models import ColumnMetadata, DatasetMetadata, GeneratedModel, MetadataContext


class DataHubMetadataProvider:
    def __init__(
        self,
        settings: Settings,
        dataset_names: list[str],
        graph: Any | None = None,
    ) -> None:
        self.settings = settings
        self.dataset_names = dataset_names
        self.graph = graph or DataHubGraph(
            DatahubClientConfig(
                server=settings.datahub_gms_url,
                token=settings.datahub_token,
            )
        )

    def retrieve(self, prompt: str) -> MetadataContext:
        mentioned = [name for name in self.dataset_names if name.lower() in prompt.lower()]
        selected = mentioned or self.dataset_names
        datasets: list[DatasetMetadata] = []
        lineage: dict[str, list[str]] = {}
        for configured_name in selected:
            qualified_name = (
                configured_name if "." in configured_name else f"main.{configured_name}"
            )
            urn = make_dataset_urn(
                self.settings.datahub_platform,
                qualified_name,
                self.settings.datahub_env,
            )
            schema = self.graph.get_aspect(urn, SchemaMetadataClass)
            if schema is None:
                raise LookupError(f"DataHub schema metadata not found for {qualified_name}")
            profile = self.graph.get_aspect(urn, DatasetProfileClass)
            upstream = self.graph.get_aspect(urn, UpstreamLineageClass)
            name = qualified_name.rsplit(".", 1)[-1]
            schema_name = qualified_name.rsplit(".", 1)[0] if "." in qualified_name else "main"
            datasets.append(
                DatasetMetadata(
                    name=name,
                    platform=self.settings.datahub_platform,
                    schema_name=schema_name,
                    columns=[
                        ColumnMetadata(
                            name=field.fieldPath,
                            native_type=field.nativeDataType,
                            nullable=field.nullable if field.nullable is not None else True,
                            description=field.description,
                            is_primary_key=bool(field.isPartOfKey),
                        )
                        for field in schema.fields
                    ],
                    row_count=profile.rowCount if profile else None,
                )
            )
            lineage[name] = [
                upstream_name
                for item in (upstream.upstreams if upstream else [])
                if (upstream_name := _dataset_name(item.dataset))
            ]
        return MetadataContext(datasets=datasets, upstream_lineage=lineage)


class DataHubPublisher:
    def __init__(self, settings: Settings, emitter: Any | None = None) -> None:
        self.settings = settings
        self.emitter = emitter or DatahubRestEmitter(
            gms_server=settings.datahub_gms_url,
            token=settings.datahub_token,
        )

    def publish(self, model: GeneratedModel, pull_request_url: str) -> str:
        dataset_name = f"main.{model.name}"
        dataset_urn = make_dataset_urn(
            self.settings.datahub_platform,
            dataset_name,
            self.settings.datahub_env,
        )
        upstreams = [
            UpstreamClass(
                dataset=make_dataset_urn(
                    self.settings.datahub_platform,
                    name if "." in name else f"main.{name}",
                    self.settings.datahub_env,
                ),
                type=DatasetLineageTypeClass.TRANSFORMED,
                auditStamp=AuditStampClass(
                    time=int(time.time() * 1000),
                    actor="urn:li:corpuser:lineageai",
                ),
            )
            for name in model.input_datasets
        ]
        aspects = [
            DatasetPropertiesClass(
                name=model.name,
                description=model.explanation or "Generated and validated by LineageAI.",
                externalUrl=pull_request_url,
                customProperties={
                    "generated_by": "LineageAI",
                    "github_pr": pull_request_url,
                },
            ),
            GlobalTagsClass(tags=[TagAssociationClass(tag=make_tag_urn("agent-generated"))]),
            UpstreamLineageClass(upstreams=upstreams),
        ]
        for aspect in aspects:
            self.emitter.emit(
                MetadataChangeProposalWrapper(
                    entityUrn=dataset_urn,
                    aspect=aspect,
                )
            )
        return dataset_urn


def _dataset_name(urn: str) -> str | None:
    key = dataset_urn_to_key(urn)
    return key.name.rsplit(".", 1)[-1] if key else None
