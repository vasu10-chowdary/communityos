const {
  initializeTestEnvironment,
  assertFails,
  assertSucceeds,
} = require("@firebase/rules-unit-testing");
const {
  doc,
  getDoc,
  setDoc,
  updateDoc,
  deleteDoc,
} = require("firebase/firestore");
const fs = require("fs");
const path = require("path");
const test = require("node:test");
const assert = require("node:assert");

const PROJECT_ID = "demo-communityos-rules-test";
let testEnv;

test.before(async () => {
  const rules = fs.readFileSync(path.join(__dirname, "firestore.rules"), "utf8");
  testEnv = await initializeTestEnvironment({
    projectId: PROJECT_ID,
    firestore: {
      rules,
      host: "127.0.0.1",
      port: 8080,
    },
  });
});

test.after(async () => {
  if (testEnv) {
    await testEnv.cleanup();
  }
});

test.beforeEach(async () => {
  await testEnv.clearFirestore();
});

test("1. Unauthenticated users cannot write incidents or access protected collections", async () => {
  const unauthed = testEnv.unauthenticatedContext();
  const db = unauthed.firestore();

  // Public incidents can be read
  await assertSucceeds(getDoc(doc(db, "incidents", "sample-inc")));

  // Unauthenticated user cannot create incident
  await assertFails(
    setDoc(doc(db, "incidents", "unauth-inc"), {
      title: "Flooding on Main St",
      description: "Severe flooding blocking all lanes of traffic.",
      reporter_id: "anon",
      status: "Reported",
    })
  );

  // Unauthenticated user cannot read private audit logs
  await assertFails(getDoc(doc(db, "audit_logs", "log-1")));

  // Unauthenticated user cannot create resources
  await assertFails(
    setDoc(doc(db, "resources", "pump-1"), {
      name: "Water Pump Alpha",
      category: "equipment",
      status: "available",
    })
  );
});

test("2. Citizens can create valid reports but cannot spoof reporter_id or pre-assign resources", async () => {
  const alice = testEnv.authenticatedContext("alice");
  const db = alice.firestore();

  // Valid report submission by alice
  await assertSucceeds(
    setDoc(doc(db, "incidents", "inc-alice-1"), {
      title: "Broken water main",
      description: "Water gushing into residential street near 5th ave.",
      reporter_id: "alice",
      status: "Reported",
      created_at: new Date().toISOString(),
    })
  );

  // Alice cannot submit report with spoofed reporter_id
  await assertFails(
    setDoc(doc(db, "incidents", "inc-alice-spoof"), {
      title: "Broken water main",
      description: "Water gushing into residential street near 5th ave.",
      reporter_id: "bob",
      status: "Reported",
    })
  );

  // Alice cannot self-assign a resource on creation
  await assertFails(
    setDoc(doc(db, "incidents", "inc-alice-selfassign"), {
      title: "Broken water main",
      description: "Water gushing into residential street near 5th ave.",
      reporter_id: "alice",
      status: "Reported",
      assigned_resource_id: "pump-1",
    })
  );

  // Alice cannot create pre-resolved incident
  await assertFails(
    setDoc(doc(db, "incidents", "inc-alice-preresolved"), {
      title: "Broken water main",
      description: "Water gushing into residential street near 5th ave.",
      reporter_id: "alice",
      status: "Resolved",
    })
  );
});

test("3. Citizens cannot edit others' data, elevate their own roles, or alter severity/status", async () => {
  // Pre-seed an incident reported by alice using security rules bypass
  await testEnv.withSecurityRulesDisabled(async (ctx) => {
    await setDoc(doc(ctx.firestore(), "incidents", "inc-100"), {
      title: "Fallen tree blocking lane",
      description: "Large oak tree fell across two lanes of traffic.",
      reporter_id: "alice",
      status: "Reported",
      severity: 3,
    });
    await setDoc(doc(ctx.firestore(), "users", "alice"), {
      name: "Alice Citizen",
      role: "citizen",
    });
  });

  const bob = testEnv.authenticatedContext("bob");
  const bobDb = bob.firestore();

  // Bob cannot modify Alice's incident
  await assertFails(
    updateDoc(doc(bobDb, "incidents", "inc-100"), {
      description: "Bob trying to edit Alice's report.",
    })
  );

  const alice = testEnv.authenticatedContext("alice");
  const aliceDb = alice.firestore();

  // Alice can update her report description
  await assertSucceeds(
    updateDoc(doc(aliceDb, "incidents", "inc-100"), {
      description: "Updated: Large oak tree fell across two lanes, power lines intact.",
    })
  );

  // Alice cannot change severity or status
  await assertFails(
    updateDoc(doc(aliceDb, "incidents", "inc-100"), {
      severity: 5,
    })
  );
  await assertFails(
    updateDoc(doc(aliceDb, "incidents", "inc-100"), {
      status: "Resolved",
    })
  );

  // Alice cannot promote herself to coordinator in users/alice
  await assertFails(
    updateDoc(doc(aliceDb, "users", "alice"), {
      role: "coordinator",
    })
  );
});

test("4. Only coordinators can manage resources and assign them to incidents", async () => {
  const citizen = testEnv.authenticatedContext("charlie");
  const coordinator = testEnv.authenticatedContext("coord1", { role: "coordinator" });

  // Citizen cannot create resource
  await assertFails(
    setDoc(doc(citizen.firestore(), "resources", "vacuum-truck-1"), {
      name: "Heavy Duty Vacuum Truck",
      category: "equipment",
      status: "Available",
    })
  );

  // Coordinator can create resource
  await assertSucceeds(
    setDoc(doc(coordinator.firestore(), "resources", "vacuum-truck-1"), {
      name: "Heavy Duty Vacuum Truck",
      category: "equipment",
      status: "Available",
    })
  );

  // Seed reported incident
  await testEnv.withSecurityRulesDisabled(async (ctx) => {
    await setDoc(doc(ctx.firestore(), "incidents", "inc-200"), {
      title: "Severe Basement Flooding",
      description: "Water levels rising quickly in residential basements.",
      reporter_id: "charlie",
      status: "Reported",
      severity: 4,
    });
  });

  // Citizen cannot assign resource or change status
  await assertFails(
    updateDoc(doc(citizen.firestore(), "incidents", "inc-200"), {
      assigned_resource_id: "vacuum-truck-1",
      assigned_resource_name: "Heavy Duty Vacuum Truck",
      status: "In Progress",
    })
  );

  // Coordinator can assign resource and update status
  await assertSucceeds(
    updateDoc(doc(coordinator.firestore(), "incidents", "inc-200"), {
      assigned_resource_id: "vacuum-truck-1",
      assigned_resource_name: "Heavy Duty Vacuum Truck",
      status: "In Progress",
    })
  );
});

test("5. Responders can update operational notes and progress but cannot alter severity or manage resources", async () => {
  const responder = testEnv.authenticatedContext("resp1", { role: "responder" });

  // Seed assigned incident
  await testEnv.withSecurityRulesDisabled(async (ctx) => {
    await setDoc(doc(ctx.firestore(), "incidents", "inc-300"), {
      title: "Blocked storm drain",
      description: "Debris clogging central stormwater runoff drain.",
      reporter_id: "alice",
      status: "Reported",
      severity: 2,
    });
  });

  // Responder can update notes and set status to In Progress
  await assertSucceeds(
    updateDoc(doc(responder.firestore(), "incidents", "inc-300"), {
      responder_notes: "Crew arrived on scene with clearing tools.",
      status: "In Progress",
      updated_at: new Date().toISOString(),
      last_updated_by: "resp1",
    })
  );

  // Responder cannot change incident severity
  await assertFails(
    updateDoc(doc(responder.firestore(), "incidents", "inc-300"), {
      severity: 5,
    })
  );

  // Responder cannot create or delete resources
  await assertFails(
    setDoc(doc(responder.firestore(), "resources", "pump-99"), {
      name: "Rogue Pump",
      status: "Available",
    })
  );
});
