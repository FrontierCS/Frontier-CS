#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>

using namespace std;

int N, R;
struct Node {
    int u, v; // children indices
};
vector<Node> slots;
vector<int> current_switches;
int current_output;

// Function to query the judge
int query(const vector<int>& s) {
    cout << "? ";
    for (int x : s) cout << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Helper to toggle a switch and update state
int toggle(int idx) {
    current_switches[idx] = 1 - current_switches[idx];
    int res = query(current_switches);
    return res;
}

string ans;
vector<char> gate_type; // '&' or '|'

void solve(int u, bool path_inverts) {
    if (u >= N) return; // Leaf

    int l = slots[u].u;
    int r = slots[u].v;

    // Check sensitivity to Left child
    // Toggle Switch L (or the switch controlling L's output)
    // Note: Switch L is at index l.
    // Toggling S_l flips the input to u from l.
    int out_orig = current_output;
    int out_l = toggle(l);
    bool sens_l = (out_l != out_orig);
    current_output = out_l; // Keep the toggled state

    // Check sensitivity to Right child
    int out_r = toggle(r);
    bool sens_r = (out_r != current_output);
    current_output = out_r; // Keep toggled state

    // Restore L to original state to analyze the (OrigL, ToggledR) config? 
    // Actually we have explored 3 states:
    // 1. Orig
    // 2. L toggled
    // 3. L toggled, R toggled
    
    // Let's deduce based on state 2 (L toggled, R original) -> out_l
    // and state 3 (L toggled, R toggled) -> out_r
    // Wait, let's look at the transitions.
    // Transition 1: Orig -> L_toggled. Delta L. (Sensitivity to L given R_orig)
    // Transition 2: L_toggled -> L_toggled, R_toggled. Delta R. (Sensitivity to R given L_toggled)
    
    // Let val_l, val_r be the inputs to gate u in the "L toggled, R toggled" state.
    // In Orig state: inputs were (not val_l, not val_r).
    // In "L toggled" state: (val_l, not val_r).
    // In "L toggled, R toggled" state: (val_l, val_r).

    // Let's analyze at state 3 (val_l, val_r).
    // Sensitivity to R (Transition 2):
    // If sensitive: 
    //   AND => val_l = 1
    //   OR  => val_l = 0
    // If not sensitive:
    //   AND => val_l = 0
    //   OR  => val_l = 1

    // Sensitivity to L (at state "R toggled", i.e., transition from (not L, R_toggled) to (L_toggled, R_toggled))?
    // We don't have that measurement directly.
    // We have Transition 1: (not val_l, not val_r) -> (val_l, not val_r).
    // This measures sens to L given (not val_r).
    
    // Let's infer type and values.
    // Let actual gate value at State 3 be G.
    // path_inverts tells us if global output == G or 1-G.
    // Let visible_G = (current_output ^ path_inverts ? 0 : 1) ... wait path_inverts is bool.
    // If path_inverts is false: Global = G.
    // If path_inverts is true: Global = 1-G.
    // Let's use `curr_val = path_inverts ? 1-current_output : current_output`.
    // Actually, XNOR: `current_output == (path_inverts ? 0 : 1)` logic.
    // Easier: int val = (current_output ^ (path_inverts ? 1 : 0));
    
    int val_3 = (current_output ^ (path_inverts ? 1 : 0)); // Value at (L_tog, R_tog)
    
    // Info from Trans 2 (sens_r): Change R while L is L_tog.
    // Inputs: (L_tog, R_orig) -> (L_tog, R_tog).
    // Sens_r true implies u is sensitive to R when L is L_tog.
    
    // Info from Trans 1 (sens_l): Change L while R is R_orig.
    // Inputs: (L_orig, R_orig) -> (L_tog, R_orig).
    // Sens_l true implies u is sensitive to L when R is R_orig.
    
    // Note: R_orig = not R_tog.
    
    // Case analysis:
    // Assume u is AND.
    // sens_r (at L_tog) => L_tog = 1.
    // !sens_r (at L_tog) => L_tog = 0.
    // sens_l (at R_orig) => R_orig = 1 => R_tog = 0.
    // !sens_l (at R_orig) => R_orig = 0 => R_tog = 1.
    
    // Assume u is OR.
    // sens_r (at L_tog) => L_tog = 0.
    // !sens_r (at L_tog) => L_tog = 1.
    // sens_l (at R_orig) => R_orig = 0 => R_tog = 1.
    // !sens_l (at R_orig) => R_orig = 1 => R_tog = 0.
    
    // Let's check consistency with value val_3 = op(L_tog, R_tog).
    
    // Hypothesis AND:
    //   Predicted L_tog = sens_r ? 1 : 0.
    //   Predicted R_tog = sens_l ? 0 : 1.
    //   Check: (Pred_L & Pred_R) == val_3 ?
    //   If match, it is AND.
    
    // Hypothesis OR:
    //   Predicted L_tog = sens_r ? 0 : 1.
    //   Predicted R_tog = sens_l ? 1 : 0.
    //   Check: (Pred_L | Pred_R) == val_3 ?
    //   If match, it is OR.
    
    // Is it possible both match?
    // Case 1: sens_r=T, sens_l=T.
    //   AND: L=1, R=0. L&R = 0.
    //   OR: L=0, R=1. L|R = 1.
    //   Distinguishable by val_3.
    
    // Case 2: sens_r=F, sens_l=F.
    //   AND: L=0, R=1. L&R = 0.
    //   OR: L=1, R=0. L|R = 1.
    //   Distinguishable by val_3.
    
    // Case 3: sens_r=T, sens_l=F.
    //   AND: L=1, R=1. L&R = 1.
    //   OR: L=0, R=0. L|R = 0.
    //   Distinguishable.
    
    // Case 4: sens_r=F, sens_l=T.
    //   AND: L=0, R=0. L&R = 0.
    //   OR: L=1, R=1. L|R = 1.
    //   Distinguishable.
    
    // So always distinguishable.
    
    int and_l = sens_r ? 1 : 0;
    int and_r = sens_l ? 0 : 1;
    bool is_and = ((and_l & and_r) == val_3);
    
    gate_type[u] = is_and ? '&' : '|';
    
    // Current inputs are (L_tog, R_tog).
    // Values are:
    //   If AND: L_tog = and_l, R_tog = and_r.
    //   If OR: L_tog = sens_r ? 0 : 1, R_tog = sens_l ? 1 : 0.
    
    int cur_l = is_and ? and_l : (sens_r ? 0 : 1);
    int cur_r = is_and ? and_r : (sens_l ? 1 : 0);
    
    // Now we need to recurse to children.
    // To solve L, we need path to L to be sensitive.
    // u is sensitive to L iff R (current) is non-blocking.
    // AND: non-blocking R is 1.
    // OR: non-blocking R is 0.
    
    int target_r = is_and ? 1 : 0;
    if (cur_r != target_r) {
        // Toggle R to make it non-blocking
        toggle(r);
        current_output = query(current_switches); // update output
        // Update cur_r
        cur_r = 1 - cur_r;
    }
    
    // Now path to L is sensitive.
    // Does path invert?
    // The path to u inverts if path_inverts is true.
    // u itself inverts? No, u is a gate.
    // But switch u is effectively part of parent's path.
    // Wait, "switch j output depends on slot j".
    // "Switch j ON: 1-x. OFF: x".
    // So if current_switches[u] is 1, u inverts.
    // Also, u might invert logic? No, AND/OR is monotonic.
    // So inversion accumulates via switches.
    // New inversion for L: path_inverts ^ (current_switches[u]==1) ^ (something about u logic?)
    // No, sensitivity is just passing the bit.
    // If u is AND and R=1, L passes through. L -> L&1 = L. No inversion.
    // If u is OR and R=0, L passes through. L -> L|0 = L. No inversion.
    // So gate logic never inverts the signal on the sensitive path.
    // Only the switch at u inverts.
    // But wait, "Slot i is connected to Ui, Vi".
    // Output of Slot i goes to Switch i.
    // Switch i feeds into parent Slot.
    // So between Slot L and Slot u, there is Switch L.
    // We already accounted for Switch L in the "toggle(l)" check?
    // No, solve(l) assumes we are at the switch L boundary.
    // The "inversion" parameter tracks if a flip in Slot L's output flips the Circuit Output.
    // Slot L output -> Switch L (inverts if ON) -> Slot u input.
    // Slot u (monotonic) -> Switch u (inverts if ON) -> ...
    // So total inversion = Sum of switch states on path.
    // We need to pass down `path_inverts ^ current_switches[u]`.
    // Wait, current_switches[l] affects L's output seen by u.
    // But solve(l) manages L.
    // Correct recursion: `solve(l, path_inverts ^ (current_switches[u] == 1))`?
    // Wait, let's verify.
    // If we flip Slot L output:
    // -> Switch L flips input to u.
    // -> Slot u output flips (since sensitive).
    // -> Switch u flips input to parent.
    // -> ...
    // -> Circuit output flips.
    // Does Switch L count?
    // Yes, solve(l) will toggle switch L to probe Slot L.
    // So we just need to know if "Switch L output flip" => "Circuit output flip".
    // From u to root, the relation is `path_inverts`.
    // u passes signal non-inverted.
    // Switch u inverts if ON.
    // So relation from "Input of u" to Root is `path_inverts ^ current_switches[u]`.
    // Switch L is at input of u.
    // So yes.
    
    solve(l, path_inverts ^ (current_switches[u] == 1));
    
    // Now solve R.
    // We need to make L non-blocking.
    // Currently L is cur_l.
    // We need L to be target_l (1 for AND, 0 for OR).
    int target_l = is_and ? 1 : 0;
    
    // Note: cur_l might have changed due to solve(l) manipulating L's subtree?
    // YES! solve(l) toggles things.
    // But solve(l) should restore? Or leave in known state?
    // My implementation of solve leaves state modified.
    // We don't know what state L is in after solve(l).
    // This is a problem.
    // We must ensure L is in a non-blocking state.
    // But we don't know the state of L's subtree output after recursion.
    // Solution:
    // We need to know L's output.
    // Since we solved L, can we force L to output a specific value?
    // Yes, if we implemented "force".
    // But simplified:
    // Just toggle L until it becomes non-blocking.
    // How to detect?
    // Toggle R to check sensitivity!
    // We want sensitivity to R.
    // While (!sensitive_to_R) { Change L }.
    // How to change L? Toggle Switch L.
    // Does toggling Switch L guarantee change?
    // Yes, Switch L inverts L's slot output. So L's contribution to u flips.
    // One of the two states is non-blocking.
    // So:
    // Check if sensitive to R (toggle R, check out).
    // If not sensitive, toggle L. Now it must be sensitive.
    // (Restore R after check).
    
    int out_test = toggle(r);
    bool is_sens_r = (out_test != current_output);
    current_output = out_test; // keep R toggled or not?
    // We want R to be "clean" for solve(R)? 
    // Actually solve(R) starts by toggling children of R.
    // It doesn't matter what state R switch is in, as long as it passes signal.
    // But for "sensitivity to R", we just proved it.
    // If is_sens_r is false, we need to fix L.
    
    if (!is_sens_r) {
        // L is blocking. Toggle L.
        toggle(l); 
        // Now L should be non-blocking.
        // And we are sensitive to R.
        // But wait, we just toggled R in the test.
        // Do we need to revert R?
        // Let's revert R to be safe/consistent?
        // Actually, just leave it. R is just a switch.
    }
    
    // Now path to R is sensitive.
    solve(r, path_inverts ^ (current_switches[u] == 1));
}

int main() {
    if (cin >> N >> R) {
        slots.resize(N);
        gate_type.resize(N);
        current_switches.assign(2 * N + 1, 0);

        for (int i = 0; i < N; ++i) {
            cin >> slots[i].u >> slots[i].v;
        }

        // Initial query to establish baseline
        cout << "? ";
        for (int x : current_switches) cout << x;
        cout << endl;
        cin >> current_output;

        solve(0, false);

        cout << "! ";
        for (int i = 0; i < N; ++i) cout << gate_type[i];
        cout << endl;
    }
    return 0;
}