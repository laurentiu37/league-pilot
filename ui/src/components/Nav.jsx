import { NavLink } from "react-router-dom";

const linkStyle = ({ isActive }) => ({
  marginRight: 12,
  textDecoration: "none",
  fontWeight: isActive ? 700 : 500,
});

export default function Nav() {
  return (
    <div style={{ marginBottom: 16, paddingBottom: 12, borderBottom: "1px solid #ddd" }}>
      <NavLink to="/simulate" style={linkStyle}>Simulate</NavLink>
      <NavLink to="/runs" style={linkStyle}>Runs</NavLink>
    </div>
  );
}