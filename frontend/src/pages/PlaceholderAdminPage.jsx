export default function PlaceholderAdminPage({ title, subtitle }) {
  return <section className='panel'>
    <h2>{title}</h2>
    <p className='muted'>{subtitle}</p>
    <div className='cards3'>
      <div className='mini-card'>Status: Active</div>
      <div className='mini-card'>Node: pve01</div>
      <div className='mini-card'>Assigned Users/Groups: Placeholder</div>
    </div>
    <div className='table-wrap'>
      <table className='table2'><thead><tr><th>Name</th><th>VMID</th><th>Node</th><th>Enabled</th><th>Assigned</th></tr></thead><tbody><tr><td>Template A</td><td>9000</td><td>pve01</td><td>Yes</td><td>Group-1</td></tr></tbody></table>
    </div>
  </section>
}
