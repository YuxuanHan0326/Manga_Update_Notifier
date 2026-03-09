export function statusText(event) {
  // Event status is derived from summary/notified timestamps to match backend semantics.
  if (!event.summarized_at) {
    return 'new'
  }
  if (!event.notified_at) {
    return 'summarized'
  }
  return 'notified'
}
