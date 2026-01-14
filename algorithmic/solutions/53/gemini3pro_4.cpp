#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <map>

using namespace std;

int query(const vector<int>& q) {
    cout << "?";
    for (int x : q) cout << " " << x;
    cout << endl;
    int ans;
    cin >> ans;
    if (ans == -1) exit(0);
    return ans;
}

void solve() {
    int n;
    cin >> n;

    // Output k = 1
    cout << 1 << endl;

    vector<int> p(n + 1, 0);
    vector<int> bad_nodes;
    vector<int> solved;

    mt19937 rng(1337);

    // Phase 1: Identify regular nodes and find their targets
    // For each u, we try to find p[u] using binary search
    // If we consistently get D=0, we mark it as a potential 2-cycle node
    
    for (int u = 1; u <= n; ++u) {
        vector<int> candidates;
        for (int i = 1; i <= n; ++i) {
            if (i != u) candidates.push_back(i);
        }

        bool is_bad = false;
        
        while (candidates.size() > 1) {
            // Try a few random splits to avoid unlucky 0s (ambiguity)
            // If it's a 2-cycle, it will always be 0.
            // If not, we have >= 50% chance to split p[u] and p^-1[u].
            
            bool split_successful = false;
            int attempts = 0;
            while (attempts < 5) {
                attempts++;
                vector<int> L, R;
                // Random shuffle
                shuffle(candidates.begin(), candidates.end(), rng);
                int mid = candidates.size() / 2;
                for (int i = 0; i < mid; ++i) L.push_back(candidates[i]);
                for (int i = mid; i < candidates.size(); ++i) R.push_back(candidates[i]);

                // Construct Q1: [others, u, L]
                // Construct Q2: [others, L, u]
                // others = R (since candidates = L u R, and u is separate)
                // Actually we need ALL numbers in permutation.
                // Q1: [R + rest_of_world, u, L]
                // But rest_of_world is constant.
                // Let's just put everything else in 'others'.
                // 'others' = {1..n} \ ({u} + L).
                // Note: R is a subset of 'others' relative to L.
                
                vector<int> others;
                vector<bool> in_L(n + 1, false);
                for (int x : L) in_L[x] = true;
                
                for (int i = 1; i <= n; ++i) {
                    if (i != u && !in_L[i]) others.push_back(i);
                }

                vector<int> q1 = others;
                q1.push_back(u);
                q1.insert(q1.end(), L.begin(), L.end());

                vector<int> q2 = others;
                q2.insert(q2.end(), L.begin(), L.end());
                q2.push_back(u);

                int ans1 = query(q1);
                int ans2 = query(q2);
                int diff = ans1 - ans2;
                // diff = (p[u] in L) - (p^-1[u] in L)

                if (diff == 1) {
                    // p[u] in L, p^-1[u] not in L
                    candidates = L;
                    split_successful = true;
                    break;
                } else if (diff == -1) {
                    // p[u] not in L (so in R), p^-1[u] in L
                    candidates = R; // R is effectively candidates \ L
                    // Reconstruct R from candidates logic above (it was shuffled)
                    // The 'candidates' variable is currently the union, we just extract R
                    // simpler:
                    vector<int> new_c;
                    for(int x : candidates) {
                         if (!in_L[x]) new_c.push_back(x);
                    }
                    candidates = new_c;
                    split_successful = true;
                    break;
                } else {
                    // diff == 0. Ambiguous or 2-cycle.
                    // Try another split.
                }
            }
            
            if (!split_successful) {
                // Consistently 0. Assume 2-cycle or inseparable.
                // With 5 attempts, probability of failure for distinct p[u], p^-1[u] is 1/32.
                // Given N=100, this is low enough risk? 
                // We mark as bad and deal later.
                is_bad = true;
                break;
            }
        }

        if (is_bad) {
            bad_nodes.push_back(u);
        } else {
            p[u] = candidates[0];
            solved.push_back(u);
        }
    }

    // Phase 2: Solve bad nodes (2-cycles)
    // We know p[u] is in bad_nodes.
    // We also know p[p[u]] = u.
    // Use binary search on bad_nodes to find partner.
    
    vector<bool> resolved(n + 1, false);
    for (int u : solved) resolved[u] = true;

    for (int u : bad_nodes) {
        if (resolved[u]) continue;

        // Partner v is in bad_nodes, not u, not resolved
        vector<int> candidates;
        for (int v : bad_nodes) {
            if (v != u && !resolved[v]) candidates.push_back(v);
        }
        
        if (candidates.empty()) {
             // Should not happen if logic is correct and N >= 4
             break;
        }
        
        // If only 1 candidate, it must be it
        while (candidates.size() > 1) {
            int mid = candidates.size() / 2;
            vector<int> V;
            for (int i = 0; i < mid; ++i) V.push_back(candidates[i]);
            
            // Query gain for set V
            // Q_blind: [u, V, others] (u at 1) -> u->v lost (0)
            // Q_active: [w, u, V, others] (w at 1) -> u->v active (1 if v not in V? No)
            
            // Let's use the specific check derived:
            // Q_blind = [u, V, rest]
            // Q_active = [w, u, V, rest]
            // If v in V:
            //   In Q_blind: u->v (lost).
            //   In Q_active: u->v (counts 1).
            //   In both: u->rest (same), rest->u (same).
            //   Wait, previous logic:
            //   Pair {u, v} gains 2 if both active vs u blind.
            //   But we don't know v.
            //   We are testing if v \in V.
            //   
            //   Let's use:
            //   Q1 = [u, V, rest]. u blind.
            //   Q2 = [w, u, V, rest]. w blind.
            //   Diff = (Total_active - 1) - (Total_active_u_blind).
            //   
            //   If v \in V:
            //     u->v is in u->V.
            //     In Q1: u is blind. u->v lost.
            //     In Q2: u active. u->v counts 1.
            //     Also v->u? v in V, u before V. v->u (target < source). No.
            //     So v->u is 0 in both (u before V).
            //     So drop is 1.
            //   If v \notin V (so v in rest):
            //     u->v is in u->rest.
            //     In Q1: u blind. u->v lost.
            //     In Q2: u active. u->v counts 1.
            //     So drop is 1.
            //   
            //   This doesn't distinguish!
            //   My previous reasoning was for checking a SPECIFIC v.
            
            //   Correct check for specific v:
            //   Q = [u, v, rest]. u blind. u->v lost. v->u lost.
            //   Q' = [w, u, v, rest]. w blind. u->v (1), v->u (1).
            //   Gain 2.
            //   
            //   Can we do this for SET V?
            //   Q_blind = [u, V, rest].
            //   Q_active = [w, u, V, rest].
            //   This doesn't work as shown.
            
            //   We need to put V such that v->u counts if active.
            //   Put V BEFORE u?
            //   Q_blind = [u, V, rest]. (u blind)
            //     v in V => v->u (0).
            //   Q_active = [w, V, u, rest]. (w blind)
            //     v in V => v before u => v->u (1).
            //     u->v (0).
            //   Compare with v in rest:
            //     Q_blind: v in rest. v->u (0).
            //     Q_active: v in rest. v->u (0).
            //   
            //   So if v in V: Q_active has +1 from v->u.
            //   What about u->v?
            //     If v in V: Q_blind (0), Q_active (0).
            //     If v in rest: Q_blind (u->rest, blind -> 0). Q_active (u->rest, 1).
            //   
            //   So:
            //   Case v in V:
            //     Q_blind: 0 interaction.
            //     Q_active: v->u (1). u->v (0). Total 1 (from u-v interaction).
            //     Plus u->rest interactions?
            //       If u->z (z in rest): Q_blind (0), Q_active (1).
            //       So Total gain = 1 (from v->u) + count(u->rest).
            //   Case v in rest:
            //     Q_blind: 0.
            //     Q_active: v->u (0). u->v (1). Total 1 (from u-v).
            //     Plus u->rest interactions (excluding v)?
            //       u->v is u->rest.
            //       u->z (z in rest, z!=v). Q_blind(0), Q_active(1).
            //     So Total gain = count(u->rest).
            //     
            //   Wait, u->v IS one of the u->rest edges.
            //   So if v in rest, gain is count(u->rest).
            //   If v in V, gain is 1 + count(u->rest).
            //   Note that count(u->rest) is number of edges from u to rest.
            //   Since u has exactly 1 outgoing edge u->v.
            //   If v in V, u->v is u->V. count(u->rest) is 0.
            //     Gain = 1 + 0 = 1.
            //   If v in rest, u->v is u->rest. count(u->rest) is 1.
            //     Gain = 1.
            //   Still 1. Distinguishing fails.
            
            //   Let's go back to linear scan for C_bad.
            //   Since N is small, maybe C_bad is very small usually.
            //   Also we have plenty queries if C_bad is small.
            //   If C_bad is large, we might TLE.
            //   But we only do linear scan on C_bad.
            //   Wait, for linear scan: Q=[u, v, rest] vs Q=[w, u, v, rest].
            //   If v is partner, diff is 2. Else 1.
            //   This is robust.
            //   Is it too slow? N pairs max. 2 queries per check.
            //   Worst case: we check all pairs.
            //   Total queries = Sum (candidates_size).
            //   Initially size N. Then N-2...
            //   This is O(N^2).
            //   We NEED binary search.
            
            //   Revisit: Q=[u, v, rest] vs [w, u, v, rest] gave 2 vs 1.
            //   The '2' comes from v->u counting.
            //   In [w, u, v, rest], u before v. u->v (1). v->u (0).
            //   Wait, previously I said v->u counts?
            //   In [w, u, v, rest], pos(u) < pos(v). v->u needs pos(v) < pos(u).
            //   So v->u is 0.
            //   So where did '2' come from?
            //   Ah, in my manual trace:
            //   If u <-> v.
            //   [w, u, v]: u->v (1). v->u (0). Total 1.
            //   [u, v]: u blind. u->v (0). v->u (0). Total 0.
            //   Diff is 1.
            //   If u not connected to z:
            //   [w, u, z]: u->v (1). v->u' (1). Total 2?
            //   No.
            
            //   Let's check u <-> v (2-cycle) vs u -> v, v -> u (disconnected).
            //   We know u, v are 2-cycles.
            //   Case 1: u <-> v.
            //     [u, v]: u->v (0), v->u (0).
            //     [w, u, v]: u->v (1), v->u (0).
            //     Drop 1.
            //   Case 2: u <-> y, v <-> z. (u, v not paired).
            //     [u, v]: u->y (in rest). (0). v->z (in rest). (1).
            //     [w, u, v]: u->y (1). v->z (1).
            //     Drop 1.
            //   
            //   It seems impossible to distinguish with just blinding u.
            //   We need to interfere with v.
            //   If we blind v?
            //   [u, v, rest] (blind u) -> u->y (0), v->z (1).
            //   [v, u, rest] (blind v) -> v->z (0), u->y (1).
            //   
            //   If u <-> v:
            //   [u, v, rest] (blind u) -> u->v (0), v->u (0). Total 0.
            //   [v, u, rest] (blind v) -> v->u (0), u->v (0). Total 0.
            //   
            //   If u <-> y, v <-> z:
            //   [u, v, rest] (blind u) -> u->y (0), v->z (1). Total 1.
            //   [v, u, rest] (blind v) -> v->z (0), u->y (1). Total 1.
            //   
            //   Distinction: 0 vs 1.
            //   Yes!
            //   If u <-> v, query returns 0.
            //   If u not paired with v, query returns 1 (assuming v->z points to rest).
            //   Since z is in rest (z != u, v), v->z points to rest.
            //   v is before rest. So v->z counts 1.
            //   So [u, v, rest] with u blind gives 0 if u <-> v, 1 otherwise.
            
            //   We can binary search!
            //   Query Q = [u, V, rest] with u blind.
            //   Count = edges from V to rest + edges from V to V.
            //   Wait, u is blind. u->anything is 0.
            //   We check if v in V is paired with u.
            //   If partner(u) in V:
            //     Let partner be y. y in V.
            //     y->u is edge y->u. u is before V (at pos 1).
            //     pos(y) > pos(u). y->u is 0.
            //     y->u doesn't contribute.
            //     y has no other edges.
            //     So y contributes 0.
            //   If partner(u) NOT in V (so in rest):
            //     y in rest. y->u. pos(y) > pos(u). 0.
            //     y contributes 0.
            //   
            //   So y contributes 0 wherever it is.
            //   Everyone else z in V has partner(z) != u.
            //   partner(z) is in V, rest, or u?
            //   partner(z) != u.
            //   So partner(z) in V or rest.
            //   z in V is before rest.
            //   If partner(z) in rest: z->partner (1).
            //   If partner(z) in V:
            //     If pos(z) < pos(partner): 1.
            //     Else 0.
            //     Sum over V is |edges in V|/2 (roughly).
            //   
            //   This depends on internal edges of V.
            //   This is complicated.
            //   
            //   However, we know V consists of 2-cycles.
            //   If we only put ONE element v in V.
            //   Q = [u, v, rest] (u blind).
            //   If u <-> v: 0.
            //   If u not<->v: v->z (1).
            //   So checking 1 element takes 1 query.
            //   We can iterate all candidates.
            //   Complexity: candidates decreases by 2 each step.
            //   Sum size is N/2 * N/2 approx N^2/4.
            //   100^2 / 4 = 2500. Too big for 1000.
            //   We really need binary search.
            
            //   Can we group V?
            //   Q = [u, V, rest]. u blind.
            //   Result = (size of V) - (number of pairs in V with pos(a)>pos(b)) - (1 if partner(u) in V).
            //   Wait, for z in V:
            //     z->partner.
            //     If partner in rest: +1.
            //     If partner in V: +1 if ordered correctly.
            //     If partner is u: 0.
            //   Since these are 2-cycles:
            //   If z in V and partner(z) in rest:
            //     Then partner(z) not in V.
            //     So split the 2-cycle.
            //     z contributes 1.
            //   If z in V and partner(z) in V:
            //     z->partner and partner->z.
            //     Exactly one counts 1.
            //     So the pair contributes 1.
            //   If z in V and partner(z) is u:
            //     z=y. y->u counts 0.
            //     y contributes 0.
            //   
            //   So, let V be a subset of candidates.
            //   Suppose V has k elements.
            //   Let m be number of 2-cycles fully within V.
            //   Let s be number of 2-cycles split (one in V, one in rest).
            //   Let y be partner(u).
            //   If y in V:
            //     y contributes 0.
            //     Other elements:
            //       2*m elements form m pairs. Count m.
            //       s elements form s pairs with rest. Count s.
            //     Total count = m + s.
            //     Note: k = 2m + s + 1.
            //     Count = (k-1) - m.
            //   If y not in V:
            //     y not involved.
            //     2*m elements -> m.
            //     s elements -> s.
            //     k = 2m + s.
            //     Count = m + s = k - m.
            //   
            //   This depends on m (internal edges).
            //   However, candidates come from bad_nodes.
            //   We don't know internal edges.
            //   BUT we can ensure m=0 by picking V such that no two elements are partners?
            //   We can't ensure that.
            //   
            //   But we can query Q_rev = [u, V_rev, rest].
            //   Reversing V changes order of internal pairs.
            //   Internal pair a->b: one order gives 1, other 0.
            //   Sum of Q(V) + Q(V_rev) relative to V?
            //   Actually, just sort V such that no pairs?
            //   
            //   Wait, simply Q1 = [u, V, rest] and Q2 = [u, V_reverse, rest].
            //   Sum = (contributions of split) * 2? No, split always 1.
            //   Sum = 2*s + (contributions of internal).
            //   Internal pair {a, b}: a->b counts in one, b->a in other?
            //   If a,b in V. a->b is 1 if a before b.
            //   In V_rev, b before a. b->a counts 1?
            //     Yes, since a->b implies b->a (2-cycle).
            //   So pair {a, b} contributes 1 to Q1 and 1 to Q2. Total 2.
            //   y->u (if y in V) contributes 0 to both.
            //   So Sum = 2*s + 2*m = 2 * (s+m).
            //   Number of elements k.
            //   If y in V: k = s + 2m + 1.
            //     Sum = 2(s+m) = k - 1 + s. (Wait, s+2m = k-1. 2s+2m = k-1+s).
            //     Sum = (k-1) + (k-1-2m) = 2k - 2 - 2m. 
            //     This is getting messy.
            //   
            //   Let's simply check elements 1 by 1.
            //   Linear scan is safe?
            //   Avg case: partner is found halfway.
            //   Queries = N + (N-2) + ... approx N^2/2.
            //   With N=100, 5000 queries. Limit 1000.
            //   Linear scan is definitely TLE.
            
            //   We must use the property: "Count = k - m if y not in V".
            //   Can we find m?
            //   We can use the "Randomized Binary Search" again!
            //   Pick random subset V.
            //   Q = [u, V, rest].
            //   Score = X.
            //   Q' = [u, rest, V]. (u blind).
            //     If y in V: y->u (0).
            //     z in V -> partner in rest => z->partner (0) (V after rest).
            //     z in V -> partner in V => pair contributes 1.
            //     z in V -> partner is u => impossible (y is unique).
            //   So Q' counts exactly m.
            //   So we can compute m!
            //   m = Ans([u, rest, V]).
            //   Then calculate Expected if y not in V: Exp = k - m.
            //   Actual = Ans([u, V, rest]).
            //   If Actual < Exp, then y is in V.
            //   Why?
            //     If y in V: count is m + s.
            //     k = 2m + s + 1 => s = k - 2m - 1.
            //     Count = m + k - 2m - 1 = k - m - 1.
            //     Exp = k - m.
            //     So Actual = Exp - 1.
            //   If y not in V:
            //     Count = k - m.
            //     Actual = Exp.
            //   
            //   Brilliant!
            //   Two queries to check if y in V.
            //   Q1 = [u, rest, V]. Gives m.
            //   Q2 = [u, V, rest]. Gives Actual.
            //   If Q2 == |V| - Q1 - 1, then y in V.
            //   Else y not in V.
            
            //   Constraint: rest must contain elements to define order.
            //   rest = candidates \ V.
            //   Need to handle empty rest?
            //   If V is all candidates, rest is empty (except solved nodes).
            //   We should include solved nodes in rest to act as spacers?
            //   Yes, 'rest' can include solved nodes. They don't interact with bad_nodes (no edges between them).
            //   Solved nodes act as sinks/sources that don't connect to V.
            //   Actually, solved nodes have edges within themselves.
            //   We should keep solved nodes constant in position.
            //   Let 'others' = solved_nodes + (candidates \ V).
            //   The formula for m only counts edges internal to V.
            //   Since solved nodes are not connected to V, edges V->solved are 0?
            //   Wait, bad nodes form 2-cycles within themselves. No edges to solved.
            //   So edges V->solved are 0.
            //   So solved nodes don't affect m or s counts except by existing.
            
            vector<int> others;
            // Add candidates not in V
            for (int i = mid; i < candidates.size(); ++i) others.push_back(candidates[i]);
            // Add solved nodes
            others.insert(others.end(), solved.begin(), solved.end());
            // Add other bad nodes not in candidates (already resolved pairs)
            for (int i=1; i<=n; ++i) {
                if (i!=u && resolved[i] && find(others.begin(), others.end(), i) == others.end()) {
                    others.push_back(i); // already added solved
                }
            }
            // Just all nodes not in V and not u
            others.clear();
            vector<bool> in_V(n + 1, false);
            for(int x : V) in_V[x] = true;
            for(int i=1; i<=n; ++i) {
                if (i != u && !in_V[i]) others.push_back(i);
            }
            
            // Q1: [u, others, V] -> counts m (internal pairs in V)
            // Note: others before V. V->others (0). others->V (0).
            vector<int> q1;
            q1.push_back(u);
            q1.insert(q1.end(), others.begin(), others.end());
            q1.insert(q1.end(), V.begin(), V.end());
            
            // Q2: [u, V, others] -> counts internal m + outgoing to others s
            vector<int> q2;
            q2.push_back(u);
            q2.insert(q2.end(), V.begin(), V.end());
            q2.insert(q2.end(), others.begin(), others.end());
            
            int m = query(q1);
            int actual = query(q2);
            int k = V.size();
            
            if (actual == k - m - 1) {
                // y in V
                candidates = V;
            } else {
                // y not in V
                // candidates = candidates \ V
                vector<int> new_c;
                for(int x : candidates) {
                    if (!in_V[x]) new_c.push_back(x);
                }
                candidates = new_c;
            }
        }
        
        int v = candidates[0];
        p[u] = v;
        p[v] = u;
        resolved[u] = true;
        resolved[v] = true;
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << p[i];
    cout << endl;
}

int main() {
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}