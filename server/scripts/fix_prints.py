import os
import re

files_to_fix = [
    'd:/Ayura AI/server/ai/llm_client.py',
    'd:/Ayura AI/server/database/chromadb_client.py',
    'd:/Ayura AI/server/routes/chat.py',
    'd:/Ayura AI/server/scripts/build_vectors.py',
    'd:/Ayura AI/server/scripts/generate_knowledge.py',
    'd:/Ayura AI/server/scripts/seed_chroma.py',
    'd:/Ayura AI/server/services/email_service.py'
]

for filepath in files_to_fix:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'import logging' not in content and 'from core.logger import logger' not in content:
        content = 'from core.logger import logger\n' + content
    
    # Simple replacement
    content = re.sub(r'print\((.*?)\)', r'logger.info(\1)', content)
    # Fix instances where it should be logger.error
    content = content.replace('logger.info(f"  [WARN]', 'logger.warning(f"')
    content = content.replace('logger.info(f"  [ERROR]', 'logger.error(f"')
    content = content.replace('logger.info("  [WARN]', 'logger.warning("')
    content = content.replace('logger.info("  [ERROR]', 'logger.error("')
    content = content.replace('logger.info(f"[ERROR]', 'logger.error(f"')
    content = content.replace('logger.info(f"[WARN]', 'logger.warning(f"')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
