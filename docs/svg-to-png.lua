local root = pandoc.system.get_working_directory()

function Image(el)
  local name = el.src:match("([^/]+)%.svg$")
  if name then
    el.src = root .. "/build/png/" .. name .. ".png"
  end
  return el
end
