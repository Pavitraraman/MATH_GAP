from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.llm import PromptVersion


class PromptService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_active_prompt(self) -> PromptVersion:
        return await self.get_prompt(settings.default_prompt_name, settings.default_prompt_version)

    async def get_prompt(self, name: str, version: str) -> PromptVersion:
        stmt = select(PromptVersion).where(
            PromptVersion.name == name,
            PromptVersion.version == version,
        )
        prompt = await self.db.scalar(stmt)
        if prompt:
            return prompt

        template_path = Path("prompts") / name / f"{version}.txt"
        template = template_path.read_text(encoding="utf-8")
        prompt = PromptVersion(
            name=name,
            version=version,
            template=template,
            metadata_json={"source": str(template_path)},
        )
        self.db.add(prompt)
        await self.db.commit()
        await self.db.refresh(prompt)
        return prompt
