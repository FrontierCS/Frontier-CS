#include <iostream>
#include <string>
#include <vector>
#include <algorithm>

using namespace std;

struct Op {
    int type;
    int pos;
};

int n;
string s1, s2;
vector<Op> ops;
string current_s;

void apply_op(int type, int pos) {
    ops.push_back({type, pos});
    // We don't necessarily need to update current_s if we trust our logic,
    // but for Op 1 decomposition it helps to track structure.
    // However, tracking string updates is O(N) per op, total O(N^2).
    // N=100k, too slow.
    // We assume the logic is correct without simulation or simulate only logically.
    // For step 1 (decomposition), we can simulate on a simplified model (vector of component sizes).
}

// Helper to decompose s1 into ()()()...
// Returns the operations to flatten s1.
void flatten_s1() {
    // We simulate the structure.
    // A valid parenthesis sequence is a list of components.
    // Each component has a size.
    // We want to reduce everything to components of size 2 "()".
    // We process from left to right.
    // If we see a component of size > 2, it is (A) where A is not empty.
    // Let this component be S. S = (A).
    // A can be decomposed into A1 A2 ...
    // S = (A1 A2 ...).
    // If we have (A1 A2 ...), we can use Op 1 to split it?
    // Op 1: (((A)B)C) -> ((A)B)(C).
    // Here outer is S. Inside is A1 A2 ...
    // We want to split off the last child of the root.
    // Let U = A1 ... Ak.
    // S = (U).
    // If k >= 2, let B = A1...Ak-1, C = Ak.
    // We need structure (((A)B)C).
    // Wait, LHS of Op 1 is (((A)B)C).
    // The outer pair is the one we are splitting? No.
    // (((A)B)C) -> ((A)B)(C).
    // The outer pair contains ((A)B) and C.
    // The result has two top-level components: ((A)B) and (C).
    // So if we have a component X = ( U V ), where V is a valid sequence (child).
    // We can split X into (U) and (V).
    // This allows us to break any (C1 C2 ... Ck) into (C1 ... Ck-1) and (Ck).
    // Then (C1 ... Ck-2) and (Ck-1), etc.
    // Eventually we get (C1), (C2), ..., (Ck).
    // Then we recursively process each (Ci).
    // If (Ci) is (), we are done with it.
    // If (Ci) is ( (Content) ), we peel it: (Content) ().
    // ((Content)) -> (Content)().
    // This is splitting ((Content)) into (Content) and ().
    // Wait, (Content) is U. () is V? No, V must be valid.
    // We need to write ((Content)) as ( U V ).
    // If Content is empty, we have (()). U=empty, V=empty? No valid V.
    // Actually ((Content)) -> (Content) () is achieved by:
    // Op 1 on (((Content)) eps ).
    // (((Content))) -> ((Content))().
    // Wait, Op 1 LHS (((A)B)C).
    // If we have ((X)), let (A)B = X, C = eps?
    // C must be valid. eps is valid.
    // So (((A)B)) -> ((A)B)().
    // So ((X)) -> (X)().
    // So we can unwrap: ((A)) -> (A) ().
    // So the strategy:
    // 1. Maintain a stack of "components to process".
    // Initially s1 is a list of components.
    // While stack not empty:
    //   Take first component C.
    //   If C is "()", move to "done" list (increment offset).
    //   Else C is "(A)".
    //     If A is empty, C is "()", handled.
    //     Else A = A1 A2 ... Ak.
    //     If k > 1:
    //       Split (A1...Ak) into (A1...Ak-1) and (Ak).
    //       Op 1 at current position.
    //       Now we have (A1...Ak-1) at pos, and (Ak) at pos + len(rest).
    //       No, (A1...Ak-1) is at pos. (Ak) is next.
    //       We keep (A1...Ak-1) as current component. Push (Ak) to "next".
    //       Actually simpler:
    //       We have components C_cur, C_next...
    //       C_cur is (A1 ... Ak).
    //       Apply Op 1. Result (A1...Ak-1) (Ak).
    //       Now we have two components.
    //       We focus on (A1...Ak-1). (Ak) is just another component following it.
    //       Repeat until C_cur is (A1).
    //     If k = 1: C = (A1).
    //       Unwrap: ((A1)) -> (A1) ().
    //       Op 1 on ((A1)).
    //       Result (A1) ().
    //       Now C_cur is A1. Next is ().
    //       Process A1.
    
    // To implement efficiently, we can parse s1 into a tree.
    // But applying ops on tree and updating indices is tricky.
    // Since N=100k, we just need to output ops.
    // We can simulate the process by tracking the recursion.
    // We track the current "global position" offset.
    // Function process(substring):
    //   Parses top level components.
    //   For each component:
    //     While component has > 1 child:
    //       Emit Op 1 at offset.
    //       Component count doubles? No, (A B) -> (A) (B).
    //       We effectively split the last child out.
    //       But Op 1 splits off the LAST child?
    //       (((A)B)C) -> ((A)B)(C).
    //       The outer parens contained ((A)B) and C.
    //       C is the last part.
    //       So yes, splits off the last child.
    //       So (C1 C2 ... Ck) -> (C1 ... Ck-1) (Ck).
    //     Now component is (C1).
    //     If C1 is not empty/atomic:
    //       Emit Op 1 at offset. ((C1)) -> (C1) ().
    //       Now we have C1 followed by ().
    //       Recursively process C1.
    //       Then process (). () is trivial.
    //       But wait, the () is at offset + len(C1).
    //       We process C1, which flattens C1 into ()...().
    //       Then the () is just another atom.
    
    // We need to calculate size of each component to know offsets.
    int pos = 0;
    vector<int> match(2 * n);
    vector<int> st;
    for (int i = 0; i < 2 * n; ++i) {
        if (s1[i] == '(') st.push_back(i);
        else {
            match[st.back()] = i;
            st.pop_back();
        }
    }

    auto getSize = [&](int start) {
        return match[start] - start + 1;
    };

    // Recursive function to process a range [l, r)
    // Returns nothing, but emits ops.
    // The structure in [l, r) is a list of valid sequences.
    // We assume the caller handles the offset correctly?
    // No, we need to track the CURRENT position of this block.
    // The block starts at `current_pos`.
    // But ops change lengths? No, flattening preserves length.
    // Flattening s1 -> s1' doesn't change 2n.
    // We simply walk through the string.
    
    // Iterative approach with explicit stack to manage "current component".
    // We scan s1.
    // If we see `( ... )`, we check inside.
    // If inside has multiple children `(A)(B)...`, we split.
    // If inside is `((...))`, we unwrap.
    // If inside is empty `()`, we skip.
    
    // Better: Recursive function `solve(l, r, offset)`
    // parses s1[l...r].
    // `offset` is the current index in the modified string.
    // For each child in s1[l...r]:
    //   If child is `()`: offset += 2.
    //   Else:
    //     Child is `( content )`.
    //     Let children of content be K.
    //     While K > 1:
    //       Op 1 at offset.
    //       Split off last child.
    //       K--;
    //     Now child is `( single_child )`.
    //     Op 1 at offset. `((X))` -> `(X)()`.
    //     Process `(X)` at `offset`.
    //     Then process `()` at `offset + len(X)`. (Trivial)
    
    // To do this, we need to quickly find children.
    // `match` array helps.
    
    // We simulate the output structure to keep track of offsets?
    // Actually, since we process left-to-right and expanding expands 'in place' (or rather, shifts tail to right),
    // and we process children recursively...
    // If we process (A B), we split to (A) (B).
    // Then process (A). (A) becomes ()()...().
    // Then process (B).
    // The offset increases by 2 for each `()` generated.
    
    struct Task {
        int l, r;
        // bool unwrap; // Do we need to unwrap this?
    };
    // Actually simpler:
    // Just traverse the tree of s1.
    // Global var `current_idx` = 0.
    // For each node:
    //   If node is leaf `()`:
    //     current_idx += 2;
    //   Else node `( children )`:
    //     For k = num_children downto 2:
    //       apply_op(1, current_idx);
    //     // Now node is `( child1 )`.
    //     apply_op(1, current_idx); // Unwrap `((child1))` -> `(child1) ()`
    //     recurse(child1);
    //     // The `()` is at current_idx (after recurse finishes).
    //     current_idx += 2; 

    auto traverse = [&](auto&& self, int l, int r) -> void {
        int idx = l;
        vector<pair<int, int>> children;
        while (idx < r) {
            int end = match[idx];
            children.push_back({idx, end + 1});
            idx = end + 1;
        }

        // Processing this list of children
        // In the flattened string, this corresponds to a contiguous range starting at `current_s_offset`.
        // We iterate through children.
        for (auto& p : children) {
            int len = p.second - p.first;
            if (len == 2) {
                // `()`
                current_s += "()"; // Logical
            } else {
                // `( content )`. content is s1[p.first+1 ... p.second-1]
                // Number of children inside?
                int inner_l = p.first + 1;
                int inner_r = p.second - 1;
                int inner_idx = inner_l;
                int count = 0;
                while (inner_idx < inner_r) {
                    count++;
                    inner_idx = match[inner_idx] + 1;
                }
                
                // Split children
                int cur_off = current_s.length();
                for (int k = 0; k < count - 1; ++k) {
                    apply_op(1, cur_off);
                }
                // Unwrap
                apply_op(1, cur_off);
                
                // Recurse on content
                self(self, inner_l, inner_r);
                
                // After recursion, we have the `()` from the unwrap
                current_s += "()";
            }
        }
    };
    
    // We need to rewrite traverse slightly because `current_s` length tracks the global offset
    // but the `children` logic depends on the *original* structure.
    // The operations change the structure.
    // The key is that `apply_op` is issued at `current_s.length()`.
    // At that moment, the component we are processing is at the head of the unprocessed suffix?
    // No, we process left-to-right. The `current_s.length()` is the start of the *current* component being processed.
    // The components to the left are fully flattened.
    // The components to the right are untouched (shifted).
    // Correct.
    
    current_s = "";
    traverse(traverse, 0, 2 * n);
}

// Build S2 from ()()...
// Ops 5, 6 allow 2 uses.
void build_s2() {
    // Parse s2 to get structure
    vector<int> match(2 * n);
    vector<int> st;
    for (int i = 0; i < 2 * n; ++i) {
        if (s2[i] == '(') st.push_back(i);
        else {
            match[st.back()] = i;
            st.pop_back();
        }
    }

    // Insert catalyst
    apply_op(5, 0); 
    // Catalyst is at 0. Unused atoms are at 2, 4, ...
    // BUT we track `current_s` logically.
    // `current_s` for us is `Catalyst` followed by `Unused`.
    // Actually, based on previous logic: `[Unused] [Built] [Catalyst]`.
    // No, `Construct(T)`: `Construct(Ck)...Construct(C1)` then Wraps then Merges.
    // The state is `[Unused Atoms] [Built Forest] [Catalyst]`.
    // `Construct` consumes from right of `Unused`.
    // Catalyst is at the right end.
    
    // To simplify: let's track the position of Catalyst.
    // Initially: `Catalyst` at 0. `Unused` at 2..2N+1.
    // We want to process `Unused` atoms.
    // But `Construct` needs `Unused` to be to the left of `Built`.
    // And `Catalyst` to the right of `Built`.
    // `Unused ... Unused Built Catalyst`.
    // Initially `Catalyst` is at 0. `Unused` is at right.
    // This is mirrored.
    // We can swap logic? No.
    // We can move Catalyst to end?
    // `Catalyst () ... ()`.
    // Can we move Catalyst to end?
    // Using Op 4? `Catalyst () ()` -> `(Catalyst ()) ()`.
    // This wraps Catalyst. Not move.
    
    // Let's assume we insert Catalyst at 2N.
    // `Unused ... Unused Catalyst`.
    // Position 2N.
    apply_op(6, 0); // Undo the op 5 above, just to reset
    apply_op(5, 2 * n); // Insert at end
    
    // Global offset for Unused atoms.
    // They are at [0, 2N).
    // `Catalyst` is at 2N.
    // We consume atoms from 2N-2, 2N-4...
    // `Construct` builds structures in the space of consumed atoms.
    // `Construct(T)` uses range `[end - len(T), end)`.
    // Catalyst is at `end`.
    // Operations use `pos = end - len`.
    
    int current_tail = 2 * n; // Position of Catalyst

    auto construct = [&](auto&& self, int l, int r) -> void {
        int len = r - l;
        if (len == 2) {
            // T = (). Consume one atom.
            current_tail -= 2;
            // Atom is at current_tail. Catalyst at current_tail + 2.
            // Nothing to do. Atom is `()`.
            return;
        }
        
        // T = (C1 ... Ck)
        // Identify children
        vector<pair<int, int>> children;
        int idx = l + 1;
        while (idx < r - 1) {
            int end = match[idx];
            children.push_back({idx, end + 1});
            idx = end + 1;
        }
        // children are C1, C2 ... Ck
        // We need to build Ck, ..., C1.
        for (int i = children.size() - 1; i >= 0; --i) {
            self(self, children[i].first, children[i].second);
        }
        
        // Now we have C1 ... Ck Catalyst
        // current_tail is at start of C1.
        // Catalyst is at current_tail + sum(len(Ci)).
        
        // Wrap C1 ... Ck
        int offset = current_tail;
        for (size_t i = 0; i < children.size(); ++i) {
            int sz = children[i].second - children[i].first;
            // C_i is at offset.
            // We want to Wrap it using atom from unused.
            // Unused is at current_tail - 2.
            // But we already consumed atoms for C_i!
            // Wait, we need to consume an EXTRA atom for the Wrap.
            // We take it from Unused (left of C1).
            current_tail -= 2;
            // Now `()` is at current_tail. `Ci` is at current_tail + 2.
            // `Catalyst` is far right?
            // No, `Wrap` uses `Op 4` on `() Ci Catalyst`?
            // `() Ci ... Catalyst`?
            // Catalyst must be adjacent?
            // We proved `() B Catalyst` -> `(B) Catalyst`.
            // But here Catalyst might be separated by `C_{i+1}...`.
            // We need a local Catalyst.
            // Do we use `C_{i+1}` as Catalyst?
            // `() Ci C_{i+1}` -> `(Ci) C_{i+1}`.
            // YES! `Op 4` `(A)(B)(C)` -> `((A)B)(C)`.
            // `A=eps`. `B=Ci`. `C=C_{i+1}`.
            // `((eps)Ci) C_{i+1}` -> `(Ci) C_{i+1}`.
            // So if `i < k-1`, we use `C_{i+1}` as catalyst.
            // If `i == k-1`, we use the main `Catalyst`.
            // So we Wrap `Ck`, then `Ck-1`, ...
            // Wait, we need to wrap C1...Ck.
            // Layout: `() C1 C2 ... Ck Catalyst`. (If we pull 1 atom).
            // We need `() C1`.
            // The `()` is at left.
            // So we can wrap `C1` using `C2`.
            // Then wrap `C2` using `C3`.
            // This order works.
            
            // Wait, logic:
            // We want `Wrap(C1)`, `Wrap(C2)`...
            // `() C1 C2 ...`
            // `() C1 C2` -> `(C1) C2`.
            // Now `(C1) () C2 ...`. No, we need another atom for C2.
            // So we assume we pulled `k` atoms.
            // `() () ... () C1 C2 ... Ck Catalyst`.
            // `() C1 C2` -> `(C1) C2`.
            // `() C2 C3` -> `(C2) C3`.
            // ...
            // `() Ck Catalyst` -> `(Ck) Catalyst`.
            
            // So we pull `k` atoms first.
            apply_op(4, current_tail);
            offset += sz + 2; // Move to next component (now wrapped)
            // But wait, `current_tail` decreased by 2.
            // The Op 4 consumed `()` and `C1` and merged.
            // Position of `(C1)` is same as `()`.
            // Next component `C2` is at `current_tail + 2 + len(C1)`.
            // After Op, `(C1)` has len `len(C1)+2`.
            // So next component is adjacent.
        }
        
        // After wrapping all: `(C1) (C2) ... (Ck) Catalyst`.
        // Merge.
        // `(C1) (C2) (C3)` -> `((C1)C2) (C3)`.
        // `((C1)C2)` is `(C1 C2)`.
        // So we merge from left.
        // `Op 4` on `(C1) (C2) (C3)`. (Uses C3 as catalyst).
        // `(C1 C2) (C3) ...`.
        // Repeat `k-1` times.
        // Last one uses Catalyst.
        
        // We need to loop.
        // `current_tail` points to `(C1)`.
        // Next is `(C2)`.
        // Perform Op 4 at `current_tail`.
        // This merges first two.
        // Repeat.
        for (size_t i = 0; i < children.size() - 1; ++i) {
            apply_op(4, current_tail);
        }
    };
    
    // We need to parse s2 children and call construct
    vector<pair<int, int>> roots;
    int idx = 0;
    while (idx < 2 * n) {
        int end = match[idx];
        roots.push_back({idx, end + 1});
        idx = end + 1;
    }
    
    for (int i = roots.size() - 1; i >= 0; --i) {
        construct(construct, roots[i].first, roots[i].second);
    }
    
    // Remove catalyst
    apply_op(6, 2 * n);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> n >> s1 >> s2)) return 0;

    flatten_s1();
    build_s2();

    cout << ops.size() << "\n";
    for (const auto& op : ops) {
        cout << op.type << " " << op.pos << "\n";
    }

    return 0;
}