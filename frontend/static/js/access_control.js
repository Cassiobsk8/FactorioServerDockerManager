         const ACCESS_CONTROL_LISTS = ["admins", "whitelist", "banlist"];
         let accessControlInitialLoad = true;

         function renderAccessControlList(list, status) {
             const countEl = document.getElementById(`${list}-count`);
             const stateEl = document.getElementById(`${list}-state`);
             const errorEl = document.getElementById(`${list}-error`);
             const listEl = document.getElementById(`${list}-list`);
             if (!countEl || !stateEl || !errorEl || !listEl) return;

             countEl.textContent = String(status.count || 0);

             if (status.error) {
                 stateEl.textContent = t("access_control.state.invalid");
                 stateEl.className = "access-control-state state-invalid";
                 errorEl.textContent = status.error;
                 errorEl.hidden = false;
                 listEl.innerHTML = "";
                 if (list === "whitelist") {
                     document.getElementById("whitelist-toggle").style.display = "none";
                     document.getElementById("whitelist-add").style.display = "none";
                 }
                 return;
             }

             errorEl.hidden = true;
             errorEl.textContent = "";

             if (list === "whitelist" && !status.exists) {
                 stateEl.textContent = t("access_control.state.disabled");
                 stateEl.className = "access-control-state state-disabled";
                 listEl.innerHTML = "";
                 document.getElementById("whitelist-toggle").style.display = "block";
                 document.getElementById("whitelist-add").style.display = "none";
                 return;
             }

             stateEl.textContent = t("access_control.state.ok");
             stateEl.className = "access-control-state state-ok";

             const records = Array.isArray(status.records) ? status.records : [];
             if (records.length === 0) {
                 const empty = document.createElement("li");
                 empty.className = "access-control-empty";
                 empty.textContent = t("access_control.empty");
                 listEl.replaceChildren(empty);
             } else {
                 const frag = document.createDocumentFragment();
                 for (const name of records) {
                     const li = document.createElement("li");
                     li.className = "access-control-item";

                     const label = document.createElement("span");
                     label.className = "access-control-item-name";
                     label.textContent = name;
                     li.appendChild(label);

                     const removeBtn = document.createElement("button");
                     removeBtn.type = "button";
                     removeBtn.className = "access-control-remove";
                     removeBtn.dataset.list = list;
                     removeBtn.dataset.name = name;
                     removeBtn.setAttribute("aria-label", t("access_control.remove"));
                     removeBtn.textContent = "×";
                     li.appendChild(removeBtn);

                     frag.appendChild(li);
                 }
                 listEl.replaceChildren(frag);
             }

             if (list === "whitelist") {
                 document.getElementById("whitelist-toggle").style.display = "none";
                 document.getElementById("whitelist-add").style.display = "flex";
             }
         }

         async function enableWhitelist() {
             const list = "whitelist";
             setAccessControlLoading(list, true);
             try {
                 const res = await fetch("/api/access-control/whitelist/enable", { method: "POST" });
                 if (!res.ok) {
                     const data = await res.json().catch(() => ({}));
                     showAccessControlError(list, data.error || t("access_control.error.failed"));
                     setAccessControlLoading(list, false);
                     return;
                 }
                 const data = await res.json();
                 if (data[list]) renderAccessControlList(list, data[list]);
             } catch (err) {
                 showAccessControlError(list, t("access_control.error.failed"));
             } finally {
                 setAccessControlLoading(list, false);
             }
         }

         async function disableWhitelist() {
             const list = "whitelist";
             const message = t("access_control.confirm_disable").replace("{list}", t("config.whitelist_title"));
             if (!confirm(message)) return;
             setAccessControlLoading(list, true);
             try {
                 const res = await fetch("/api/access-control/whitelist/disable", { method: "DELETE" });
                 if (!res.ok) {
                     const data = await res.json().catch(() => ({}));
                     showAccessControlError(list, data.error || t("access_control.error.failed"));
                     setAccessControlLoading(list, false);
                     return;
                 }
                 const data = await res.json();
                 if (data[list]) renderAccessControlList(list, data[list]);
             } catch (err) {
                 showAccessControlError(list, t("access_control.error.failed"));
             } finally {
                 setAccessControlLoading(list, false);
             }
         }

         function setAccessControlLoading(list, loading) {
             const loadingEl = document.getElementById(`${list}-loading`);
             if (loadingEl) {
                 loadingEl.classList.toggle("active", loading);
             }

             const input = document.getElementById(`${list}-input`);
             const saveBtn = document.getElementById(`${list}-save`);
             const cancelBtn = document.getElementById(`${list}-cancel`);
             const disableBtn = document.getElementById(`${list}-disable`);

             if (input) input.disabled = loading;
             if (saveBtn) saveBtn.disabled = loading;
             if (cancelBtn) cancelBtn.disabled = loading;
             if (disableBtn) disableBtn.disabled = loading;

             document.querySelectorAll(`.access-control-remove[data-list="${list}"]`).forEach((btn) => {
                 btn.disabled = loading;
             });
         }

         async function fetchAccessControl() {
             const isInitial = accessControlInitialLoad;
             if (isInitial) {
                 for (const list of ACCESS_CONTROL_LISTS) {
                     setAccessControlLoading(list, true);
                 }
             }
             try {
                 const res = await fetch("/api/access-control");
                 if (!res.ok) return;
                 const data = await res.json();
                 for (const list of ACCESS_CONTROL_LISTS) {
                     const status = data[list];
                     if (status) renderAccessControlList(list, status);
                 }
             } catch (err) {
                 // ignore; keep last known state
             } finally {
                 if (isInitial) {
                     for (const list of ACCESS_CONTROL_LISTS) {
                         setAccessControlLoading(list, false);
                     }
                     accessControlInitialLoad = false;
                 }
             }
         }

         function friendlyAccessControlError(error) {
             if (!error) return t("access_control.error.failed");

             const duplicateMatch = error.match(/Duplicate entry: (.+)/i);
             if (duplicateMatch) {
                 return t("access_control.error.duplicate").replace("{name}", duplicateMatch[1]);
             }

             const notFoundMatch = error.match(/Entry not found: (.+)/i);
             if (notFoundMatch) {
                 return t("access_control.error.not_found").replace("{name}", notFoundMatch[1]);
             }

             const lower = error.toLowerCase();
             if (lower.includes("name is required") || lower.includes("cannot be empty")) {
                 return t("access_control.error.empty");
             }

             return error;
         }

         function showAccessControlError(list, message) {
             const errorEl = document.getElementById(`${list}-error`);
             if (!errorEl) return;
             errorEl.textContent = message;
             errorEl.hidden = false;
         }

         async function addAccessControlEntry(list) {
             const input = document.getElementById(`${list}-input`);
             if (!input) return;
             const name = input.value.trim();
             if (!name) {
                 showAccessControlError(list, t("access_control.error.empty"));
                 return;
             }
             setAccessControlLoading(list, true);
             try {
                 const res = await fetch(`/api/access-control/${list}`, {
                     method: "POST",
                     headers: { "Content-Type": "application/json" },
                     body: JSON.stringify({ name }),
                 });
                 if (!res.ok) {
                     const data = await res.json().catch(() => ({}));
                     showAccessControlError(list, friendlyAccessControlError(data.error || t("access_control.error.failed")));
                     setAccessControlLoading(list, false);
                     return;
                 }
                 input.value = "";
                 const data = await res.json();
                 if (data[list]) renderAccessControlList(list, data[list]);
             } catch (err) {
                 showAccessControlError(list, t("access_control.error.failed"));
             } finally {
                 setAccessControlLoading(list, false);
             }
         }

         function cancelAccessControlEntry(list) {
             const input = document.getElementById(`${list}-input`);
             if (input) input.value = "";
             const errorEl = document.getElementById(`${list}-error`);
             if (errorEl) errorEl.hidden = true;
         }

         async function removeAccessControlEntry(list, name) {
             const listTitle = t(`config.${list}_title`);
             if (!confirm(t("confirm.remove_access").replace("{list}", listTitle).replace("{name}", name))) {
                 return;
             }
             setAccessControlLoading(list, true);
             try {
                 const res = await fetch(`/api/access-control/${list}`, {
                     method: "DELETE",
                     headers: { "Content-Type": "application/json" },
                     body: JSON.stringify({ name }),
                 });
                 if (!res.ok) {
                     const data = await res.json().catch(() => ({}));
                     showAccessControlError(list, friendlyAccessControlError(data.error || t("access_control.error.failed")));
                     setAccessControlLoading(list, false);
                     return;
                 }
                 const data = await res.json();
                 if (data[list]) renderAccessControlList(list, data[list]);
             } catch (err) {
                 showAccessControlError(list, t("access_control.error.failed"));
             } finally {
                 setAccessControlLoading(list, false);
             }
         }

         for (const list of ACCESS_CONTROL_LISTS) {
             const saveBtn = document.getElementById(`${list}-save`);
             const cancelBtn = document.getElementById(`${list}-cancel`);
             const input = document.getElementById(`${list}-input`);

             if (saveBtn) {
                 saveBtn.addEventListener("click", () => addAccessControlEntry(list));
             }
             if (cancelBtn) {
                 cancelBtn.addEventListener("click", () => cancelAccessControlEntry(list));
             }
             if (input) {
                 input.addEventListener("keydown", (e) => {
                     if (e.key === "Enter") {
                         e.preventDefault();
                         addAccessControlEntry(list);
                     }
                     if (e.key === "Escape") {
                         cancelAccessControlEntry(list);
                     }
                 });
             }
         }

         const whitelistEnableBtn = document.getElementById("whitelist-enable");
         if (whitelistEnableBtn) {
             whitelistEnableBtn.addEventListener("click", enableWhitelist);
         }

         const whitelistDisableBtn = document.getElementById("whitelist-disable");
         if (whitelistDisableBtn) {
             whitelistDisableBtn.addEventListener("click", disableWhitelist);
         }

          document.addEventListener("click", (e) => {
              const removeBtn = e.target.closest(".access-control-remove");
              if (removeBtn) {
                  const { list, name } = removeBtn.dataset;
                  if (list && name) removeAccessControlEntry(list, name);
              }
          });

          fetchAccessControl();
          setInterval(fetchAccessControl, 5000);

          async function fetchRuntimeState() {
              try {
                  const res = await fetch("/api/runtime-state");
                  if (!res.ok) return;
                  const data = await res.json();
                  updateWhitelistRuntimeBadge(data);
              } catch (err) {
                  // ignore
              }
          }

          function updateWhitelistRuntimeBadge(runtime) {
              const badge = document.getElementById("whitelist-runtime-badge");
              if (!badge) return;
              const hasPending = Boolean(runtime && runtime.has_pending && runtime.pending_keys && runtime.pending_keys.includes("whitelist"));
              if (hasPending) {
                  badge.textContent = t("status.runtime.restart_required");
                  badge.style.display = "";
                  badge.className = "access-control-runtime-badge";
              } else {
                  badge.textContent = t("status.runtime.applied");
                  badge.style.display = "none";
                  badge.className = "access-control-runtime-badge applied";
              }
          }

          fetchRuntimeState();
          setInterval(fetchRuntimeState, 5000);
