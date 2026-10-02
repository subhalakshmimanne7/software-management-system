/* Modal helpers */
function openModal(id) {
  var m = document.getElementById(id);
  if (m) { m.classList.add('active'); m.style.display = 'flex'; }
}
function closeModal(id) {
  var m = document.getElementById(id);
  if (m) { m.classList.remove('active'); m.style.display = 'none'; }
}
function confirmDelete(type, name) {
  return confirm('Delete ' + type + ' "' + name + '"? This cannot be undone.');
}

/* Small utilities */
function el(id) { return document.getElementById(id); }
function setVal(id, v) {
  var e = el(id);
  if (e) e.value = (v === null || v === undefined || v === 'None') ? '' : v;
}
function openEdit(modalId, formId, action) {
  el(formId).action = action;
  openModal(modalId);
}

/* Populate edit modals (form action -> /<listing>/edit/<id>) */
function populateEditDepartment(id, name, desc, loc, email) {
  setVal('edit_dept_name', name); setVal('edit_dept_desc', desc);
  setVal('edit_dept_location', loc); setVal('edit_dept_email', email);
  openEdit('editDeptModal', 'editDeptForm', '/departments/edit/' + id);
}
function populateEditProject(id, name, desc, start, end, status, deptId) {
  setVal('edit_project_name', name); setVal('edit_project_desc', desc);
  setVal('edit_project_start', start); setVal('edit_project_end', end);
  setVal('edit_project_status', status); setVal('edit_project_dept', deptId);
  openEdit('editProjectModal', 'editProjectForm', '/projects/edit/' + id);
}
function populateEditDeveloper(id, name, email) {
  setVal('edit_dev_name', name); setVal('edit_dev_email', email);
  openEdit('editDeveloperModal', 'editDeveloperForm', '/developers/edit/' + id);
}
function populateEditSoftware(id, name, desc, status, projectId, techJson) {
  setVal('edit_software_name', name); setVal('edit_software_desc', desc);
  setVal('edit_software_status', status); setVal('edit_software_project', projectId);
  var ids = [];
  try { ids = JSON.parse(techJson).map(String); } catch (e) {}
  document.querySelectorAll('#editSoftwareForm input[name="technologies"]').forEach(function (c) {
    c.checked = ids.indexOf(c.value) !== -1;
  });
  openEdit('editSoftwareModal', 'editSoftwareForm', '/software/edit/' + id);
}
function populateEditVersion(id, softwareId, number, date) {
  setVal('edit_version_software', softwareId); setVal('edit_version_number', number);
  setVal('edit_version_release', date);
  openEdit('editVersionModal', 'editVersionForm', '/versions/edit/' + id);
}
function populateEditTechnology(id, name, type, version, desc) {
  setVal('edit_tech_name', name); setVal('edit_tech_type', type);
  setVal('edit_tech_version', version); setVal('edit_tech_desc', desc);
  openEdit('editTechnologyModal', 'editTechnologyForm', '/technologies/edit/' + id);
}
function populateEditLicense(id, softwareId, type, start, expiry, status) {
  setVal('edit_license_software', softwareId); setVal('edit_license_type', type);
  setVal('edit_license_start', start); setVal('edit_license_expiry', expiry);
  setVal('edit_license_status', status);
  openEdit('editLicenseModal', 'editLicenseForm', '/licenses/edit/' + id);
}
function populateEditBug(id, softwareId, desc, severity, status, date) {
  setVal('edit_bug_software', softwareId); setVal('edit_bug_desc', desc);
  setVal('edit_bug_severity', severity); setVal('edit_bug_status', status);
  setVal('edit_bug_date', date);
  openEdit('editBugModal', 'editBugForm', '/bugs/edit/' + id);
}
function populateEditMaintenance(id, bugId, date, desc, devId, status) {
  setVal('edit_maint_bug', bugId); setVal('edit_maint_date', date);
  setVal('edit_maint_desc', desc); setVal('edit_maint_performed', devId);
  setVal('edit_maint_status', status);
  openEdit('editMaintenanceModal', 'editMaintenanceForm', '/maintenance/edit/' + id);
}
function populateEditUser(id, name, email) {
  setVal('edit_user_name', name); setVal('edit_user_email', email); setVal('edit_user_password', '');
  openEdit('editUserModal', 'editUserForm', '/users/edit/' + id);
}

/* Close modals on backdrop click / Escape, dismiss alerts */
document.addEventListener('click', function (e) {
  if (e.target.classList && e.target.classList.contains('modal-overlay')) closeModal(e.target.id);
  if (e.target.classList && e.target.classList.contains('alert-close')) e.target.parentElement.remove();
});
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') document.querySelectorAll('.modal-overlay.active').forEach(function (m) { closeModal(m.id); });
});
