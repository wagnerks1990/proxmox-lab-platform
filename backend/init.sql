INSERT INTO roles (name) VALUES ('Student'), ('Teacher'), ('Admin') ON CONFLICT DO NOTHING;

INSERT INTO users (username,email,password_hash,role_id)
VALUES
('alice','alice@example.edu','$2b$12$4YhPUD3t8f70JY7V2zNnD.8bhgXqqPp6j8cgqWOmXDVvw8O3krzxS',1),
('teacher1','teacher1@example.edu','$2b$12$4YhPUD3t8f70JY7V2zNnD.8bhgXqqPp6j8cgqWOmXDVvw8O3krzxS',2),
('admin1','admin1@example.edu','$2b$12$4YhPUD3t8f70JY7V2zNnD.8bhgXqqPp6j8cgqWOmXDVvw8O3krzxS',3)
ON CONFLICT DO NOTHING;

INSERT INTO vm_templates (name, proxmox_node, source_vmid) VALUES
('ubuntu-lab','pve1',9000),
('windows-lab','pve1',9001)
ON CONFLICT DO NOTHING;

INSERT INTO permissions (user_id, template_id) VALUES (1,1), (1,2) ON CONFLICT DO NOTHING;
