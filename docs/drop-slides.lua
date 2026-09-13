-- Report build: a slide block restates the chapter it lives in, so the PDF
-- drops it. The deck keeps only these blocks (see deck-slides.lua), which is
-- what stops the two deliverables from drifting apart: there is one source.
function Div(el)
  if el.classes:includes("deck-slide") then
    return {}
  end
end
