export default function(component) {
  const {data, parentElement, setTriggerValue} = component;
  const root = parentElement.querySelector('#surface');
  // All dynamic values in this markup are escaped by the Python templates.
  root.innerHTML = data.html;
  const names = {text:'--ink',muted:'--muted',line:'--line',bg:'--paper',accent:'--accent',card:'--card'};
  for (const [key, variable] of Object.entries(names)) root.style.setProperty(variable, data.colors[key]);
  const click = event => {
    const button = event.target.closest('button[data-action]');
    if (!button || !root.contains(button)) return;
    setTriggerValue('action', {kind: button.dataset.action, id: button.dataset.id || ''});
  };
  root.addEventListener('click', click);
  return () => root.removeEventListener('click', click);
}
