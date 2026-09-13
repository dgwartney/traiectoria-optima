-- Deck build: keep only the `deck-slide` blocks, and write each one out as its
-- own markdown file so a slide can be hand-tuned after the fact without
-- touching the chapter it came from.
--
-- Authoring shape, inside a report chapter:
--
--     <div class="deck-slide" id="cleaning">
--
--     ### Cleaning: what got dropped and why
--
--     ...body...
--
--     </div>
--
-- The blank lines are load-bearing. CommonMark ends an HTML block at a blank
-- line, so GitHub renders the inner markdown and hides the wrapper, while
-- pandoc parses the whole thing as a native Div. Without them pandoc takes it
-- as one raw HTML block and the slide vanishes from the deck with no error --
-- which is what tests/deck/test_slide_markup.py exists to catch.
--
-- The `###` heading is the slide title. It is demoted to `##` on the way out,
-- because the reveal.js writer starts a new `<section>` at --slide-level=2.

local outdir = os.getenv("DECK_SLIDES_DIR") or "build/deck"

local writer_options = pandoc.WriterOptions({ wrap_text = "none" })

local collected = {}

function Div(el)
  if el.classes:includes("deck-slide") then
    table.insert(collected, el)
  end
end

local function slide_document(el)
  local title = nil
  local body = {}
  for _, block in ipairs(el.content) do
    if title == nil and block.t == "Header" then
      title = block
    else
      table.insert(body, block)
    end
  end
  if title == nil then
    error(("deck-slide '%s' has no heading to use as its title"):format(el.identifier))
  end
  local blocks = pandoc.Blocks({ pandoc.Header(2, title.content, pandoc.Attr(el.identifier)) })
  blocks:extend(body)
  return pandoc.Pandoc(blocks)
end

function Pandoc(doc)
  if #collected == 0 then
    error("no deck-slide blocks found in the chapters")
  end
  local names = {}
  for _, el in ipairs(collected) do
    if el.identifier == "" then
      error("every deck-slide needs an id: it is the slide's name in docs/deck/manifest.txt")
    end
    if names[el.identifier] then
      error(("two deck-slide blocks share the id '%s'"):format(el.identifier))
    end
    names[el.identifier] = true
    local path = outdir .. "/" .. el.identifier .. ".md"
    local handle = assert(io.open(path, "w"))
    handle:write(pandoc.write(slide_document(el), "markdown", writer_options))
    handle:close()
  end
  return doc
end
