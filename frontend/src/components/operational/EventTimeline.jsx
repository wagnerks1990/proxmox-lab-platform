export default function EventTimeline({items=[]}){return <ul>{items.map((i,idx)=><li key={idx}>{i}</li>)}</ul>}
