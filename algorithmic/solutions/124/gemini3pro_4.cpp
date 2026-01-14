#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

// Function to query
int query(const vector<int>& indices) {
    cout << "? " << indices.size();
    for (int idx : indices) {
        cout << " " << idx;
    }
    cout << endl;
    int res;
    cin >> res;
    return res;
}

int main() {
    int n;
    if (!(cin >> n)) return 0;

    // Step 1: Find candidates for 1 and N
    // Using query of size n-1. 
    // Sum of all p is n(n+1)/2. 
    // Avg of n-1 is integer iff (Sum - p_i) % (n-1) == 0.
    // Sum = n(n+1)/2. n=2k. Sum = k(2k+1) = 2k^2 + k.
    // n-1 = 2k-1.
    // Sum = k(2k-1) + 2k = k(n-1) + n = k(n-1) + (n-1) + 1.
    // Sum = (k+1)(n-1) + 1.
    // So Sum == 1 (mod n-1).
    // Condition: 1 - p_i == 0 (mod n-1) => p_i == 1 (mod n-1).
    // In range [1, n], only 1 and n satisfy this (since n = 1 + (n-1)).
    // So this identifies {1, n}.

    vector<int> candidates;
    if (n == 2) {
        // Trivial case
        cout << "! 1 2" << endl;
        return 0;
    }

    for (int i = 1; i <= n; ++i) {
        vector<int> q;
        for (int j = 1; j <= n; ++j) {
            if (i != j) q.push_back(j);
        }
        if (query(q)) {
            candidates.push_back(i);
        }
    }

    // There should be exactly 2 candidates
    int u = candidates[0];
    int v = candidates[1];

    // Step 2: Parity partition
    // Assume u is 1 (odd) and v is n (even).
    // We will verify this assumption or swap later implicitly by the final check.
    // Partition others based on parity relative to u.
    vector<int> O, E;
    O.push_back(u);
    E.push_back(v);

    for (int i = 1; i <= n; ++i) {
        if (i == u || i == v) continue;
        // Query {u, i}. If 1, same parity as u (odd). If 0, diff parity (even).
        if (query({u, i})) {
            O.push_back(i);
        } else {
            E.push_back(i);
        }
    }

    // Now solve for O and E
    // Helper lambda to solve a set
    // indices: the subset of indices
    // is_odd: true if solving for odd numbers, false for even
    // known_1: index of 1
    // known_n: index of n
    vector<int> p(n + 1);
    
    auto solve = [&](vector<int>& indices, bool is_odd) {
        int k = indices.size();
        if (k == 0) return;
        if (k == 1) {
            // Only happens for N=2 which is handled.
            // Or edge cases. But with N>=2 even, K=N/2 >= 1.
            // For N=2, K=1, modulus 0 error. Handled N=2 separately.
            return; 
        }
        
        long long sum_vals = 0;
        if (is_odd) {
            // Sum of 1, 3, ..., 2k-1 is k^2
            sum_vals = (long long)k * k;
        } else {
            // Sum of 2, 4, ..., 2k is k(k+1)
            sum_vals = (long long)k * (k + 1);
        }
        
        int mod = k - 1; 
        // If mod == 0 (k=1), handled.

        // We query indices \ {i} for each i.
        // Sum - p_i == 0 (mod k-1).
        // p_i == Sum (mod k-1).
        // Precompute Sum % (k-1).
        int target_rem = sum_vals % mod;
        
        map<int, int> remainder_to_idx;
        for (int idx : indices) {
            vector<int> q;
            for (int other : indices) {
                if (idx != other) q.push_back(other);
            }
            if (q.empty()) continue; // Should not happen given k > 1
            
            // Query tells us if (Sum - p_i) % mod == 0
            // This is boolean.
            // Wait, previous logic relied on unique remainders.
            // The query only gives 1 bit!
            // Correct approach for step 3:
            // The query "indices \ {i}" returns 1 iff p_i == Sum (mod mod).
            // This only identifies p_i such that p_i % mod == target_rem.
            // This does NOT give p_i for everyone.
            // THIS WAS THE FLAW IN THE THOUGHT PROCESS.
            // However, we can construct the specific sums?
            // No, interactive problem.
            
            // Re-evaluating with limited queries.
            // Actually, we can use u and v to get mod 3?
            // With O(N) queries we can get p_i mod 3 for everyone.
            // With p_i mod 2 (parity), p_i mod 3, p_i mod (something else)?
            // With u=1, v=N.
            // {u, v, i} gives p_i mod 3.
            // If N is large, CRT needs more primes. 3, 4, 5, 7 gives 420.
            // 3, 4, 5, 7, 9? lcm(3,4,5,7) = 420.
            // We need up to 800.
            // Use moduli.
            // Mod 2: Parity (Done).
            // Mod 3: Query {u, v, i}. Sum 1+N+p_i. Check % 3 == 0.
            // We can shift sum by adding dummy? No dummy.
            // But we can check p_i % 3 == (-1-N)%3.
            // What about p_i % 3 != ...?
            // This boolean check is weak.
            
            // FALLBACK to the O(N) logic for N divisible by 4.
            // If N % 4 == 0, then K is even, K-1 is odd.
            // d=2. gcd(2, K-1)=1.
            // Remainder unique.
            // BUT the query is boolean. It only checks IF remainder matches.
            // It does not RETURN the remainder.
            // So we can only find elements with specific remainder.
            // This strategy fails.
        }
    };
    
    // Correct strategy given the constraints and scoring:
    // We must identify elements one by one or by small groups.
    // We have 1 and N.
    // Use them to search for 2, 3, etc.
    // To find x, knowing 1..x-1 and N..N-x+1?
    // We established this is O(N^2).
    // But maybe for N=800, N^2/4 is acceptable?
    // 160,000 queries. 4 seconds is plenty for 1e5-2e5 queries IO?
    // IO is slow. fflush every time.
    // 160,000 flushes might be TLE.
    // Usually interactive limit ~10000 queries.
    // The reference solution must be O(N).
    
    // Real O(N) strategy:
    // 1. Find 1 and N (candidates u, v).
    // 2. Determine parities relative to u.
    // 3. For every i, determine p_i % 3.
    //    Query {u, v, i}. Sum 1 + N + p_i.
    //    If N%3 == 0: 1 + p_i = 0 mod 3 => p_i = 2 mod 3.
    //    If N%3 == 1: 2 + p_i = 0 mod 3 => p_i = 1 mod 3.
    //    If N%3 == 2: p_i = 0 mod 3.
    //    So we find indices with specific mod 3.
    //    We can't find ALL mod 3.
    
    // There is no obvious O(N) strategy without finding values directly.
    // BUT notice the constraints: n <= 800.
    // Maybe we just peel using the "All except i" but for specific targets?
    // The query (Set \ {i}) checks if p_i has a specific remainder.
    // If we vary the Set, we vary the target remainder.
    // Set S. Check p_i = Sum(S) mod (|S|-1).
    // If we remove an element from S, Sum changes.
    // Let S_full = O. Sum_O.
    // Target rem R0 = Sum_O % (K-1).
    // Checks p_i = R0.
    // Try S' = O \ {j} (where j is known).
    // Sum' = Sum_O - p_j. Size K-1. Mod K-2.
    // Target R1 = (Sum_O - p_j) % (K-2).
    // Checks p_i = R1 mod (K-2).
    // With a few such checks, we can pin down p_i using CRT-like intersection of candidates.
    // We know p_i is odd.
    // Check p_i = R0 mod K-1.
    // Check p_i = R1 mod K-2.
    // Check p_i = R2 mod K-3.
    // Candidates decrease rapidly.
    // For N=800, K=400. K-1=399, K-2=398.
    // LCM is large. Intersection is likely unique.
    // We need to know p_j to form S'.
    // We know 1.
    // So we can perform check with O and O \ {1}.
    // This gives p_i mod 399 and p_i mod 398.
    // This should uniquely identify p_i.
    // We perform 2 queries per element. Total 2N.
    // This is the solution!

    // Implementation of CRT strategy
    // We have O and E.
    // For O:
    // 1. Query O \ {i} for all i.
    //    Returns true if p_i == Sum(O) mod (K-1).
    //    Wait, boolean return.
    //    We need to FIND the remainder.
    //    We cannot find the remainder with boolean queries unless we try all remainders?
    //    We can't change the sum easily.
    
    // What if we try adding known elements?
    // We have u=1, v=N.
    // Add v to O?
    // S = O U {v}. Size K+1. Mod K.
    // Sum = Sum(O) + N.
    // Check p_i == (Sum(O)+N) mod K.
    // S2 = O U {v} \ {u}. Size K. Mod K-1.
    // Sum = Sum(O) + N - 1.
    // Check p_i == (Sum(O)+N-1) mod K-1.
    // This is still just checking specific remainders.
    // We won't find p_i for most i.
    
    // BACKTRACK.
    // If n <= 800, and 4 sec.
    // N^2 / C is acceptable.
    // Peeling strategy:
    // Find min and max of O. (1 and N-1).
    // Remove them.
    // Find min and max of remainder. (3 and N-3).
    // Remove them.
    // ...
    // How to find min/max?
    // Query "Set \ {i}".
    // For O (size K), sum is K^2.
    // Target rem = K^2 % (K-1) = 1.
    // Values are 1, 3, ..., 2K-1.
    // 1 = 1. (Match)
    // 2K-1 = 2(K-1) + 1 = 1. (Match)
    // All others: 2j-1. 2j-1 = 1 mod K-1 => 2j-2 = 0 => 2(j-1) divisible by K-1.
    // For j in [2, K-1], 2(j-1) < 2K-2.
    // Divisible only if 2(j-1) = K-1 or 0.
    // If K-1 is even (K odd), then j-1 = (K-1)/2 is possible.
    // If K-1 is odd (K even), only 0.
    // Case 1: K even (N div 4). Only j=1 and j=K match. (Values 1 and 2K-1).
    // Case 2: K odd (N=4k+2). j=1, j=K, and j=(K+1)/2 match.
    // So query identifies 2 or 3 elements (Min, Max, Mid).
    // We remove them and repeat.
    // This costs |S| queries per layer.
    // Total O(N^2).
    // 160000 is likely OK.
    
    // Solve O:
    vector<int> current_O = O;
    // We need to associate indices with values.
    // Initially we don't know values.
    // We just know current_O contains some odd values.
    // They are a contiguous range of odds?
    // Yes, initially 1..N-1.
    // If we peel 1 and N-1, we get 3..N-3.
    // So at each step, we know the min and max values available.
    // We find indices for min and max (and mid).
    // Assign values. Remove indices. Repeat.
    
    int min_val_O = 1;
    int max_val_O = n - 1;
    
    while (!current_O.empty()) {
        int k = current_O.size();
        if (k == 0) break;
        if (k == 1) {
            p[current_O[0]] = min_val_O; // Only one left
            break;
        }
        
        // Target candidates
        vector<int> matched;
        for (int idx : current_O) {
            // Query current_O \ {idx}
            // Size k-1.
            // If k=2, size 1. Query {other}. Avg int => p_other % 1 == 0. Always true.
            // Size 1 query always returns 1.
            // So if k=2, both match.
            // Indices are min and max.
            // Distinguish using u (1) and v (N).
            
            vector<int> q;
            for (int other : current_O) {
                if (other != idx) q.push_back(other);
            }
            if (query(q)) {
                matched.push_back(idx);
            }
        }
        
        // matched contains indices of min, max (and mid if k odd)
        // If k=2, matched has 2.
        // We know min_val_O and max_val_O.
        // And mid_val if exists.
        
        // Distinguish matched indices
        // Use known u=1, v=N.
        // If we found 1 earlier, u is correct.
        // Check p_x against u or v.
        // p_x is odd.
        // query {u, v, x} -> 1+N+p_x % 3 == 0.
        // This gives p_x % 3.
        // If min_val, max_val, mid_val have diff mod 3, we are good.
        // If collision mod 3, use mod 4 or 5?
        // Actually simple: compare with min_val_O.
        // We assume p_x takes one of the candidate values.
        
        // Candidates values:
        vector<int> vals;
        vals.push_back(min_val_O);
        vals.push_back(max_val_O);
        // If k is odd, check mid
        // Mid logic: 2(j-1) = k-1. j = (k-1)/2 + 1 = (k+1)/2.
        // Value = min + 2*(j-1)*step? 
        // Initial step 2.
        // Values are min, min+2d, min+4d...
        // Actually the set is always an arithmetic progression?
        // Yes, removing min/max preserves AP.
        // current step d.
        // 2(j-1) = k-1 is condition for remainder match.
        // Value at j: min + (j-1)*d.
        // Mid value: min + (k-1)/2 * d.
        // Only if k is odd.
        
        // So we have 2 or 3 candidate values.
        // We have matched indices.
        // Map indices to values.
        // Try to distinguish using p_x % 3.
        
        // If mod 3 fails, try {u, x} (mod 2) - useless.
        // Try {u, u2, x} where u2 is another known?
        // We know p[u] = 1.
        // Just use brute force check against all available moduli if needed?
        // Or just assume n is large enough that collision is rare?
        
        // Let's implement robust distinguisher:
        // For each idx in matched, test compatibility with val in vals.
        // Compatibility test:
        // Use mod 3 query.
        // Maybe also mod 4 (using sum of 4? No).
        
        // Actually, for k=2, we have 2 indices, 2 values.
        // min, max.
        // min < max.
        // check x vs min.
        // If we can determine x < y?
        // Hard.
        
        // What if we just output ! ... at end and hope for the best?
        // No, need to be correct.
        
        // Special case: k=2.
        // Vals v1, v2. Indices i1, i2.
        // Query {u, v, i1}. Res1.
        // Exp1 = (1 + N + v1) % 3 == 0.
        // Exp2 = (1 + N + v2) % 3 == 0.
        // If Exp1 != Exp2, and Res1 matches Exp1, then i1 is v1.
        // If collision, we need another query.
        // We have p filled with knowns?
        // Use any known p_k.
        // Query {k, i1}. (1+p_k+v1)%3... no query size 2.
        // Query {u, k, i1}.
        // Iterate knowns until distinguished.
        
        // Filter matched to only valid ones
        // Sometimes non-min/max might appear? No, math says only these.
        
        // Handle odd k mid value.
        long long current_d = (max_val_O - min_val_O) / (k - 1);
        if (k % 2 != 0) {
            vals.push_back(min_val_O + (k - 1) / 2 * current_d);
        }
        
        // Distinguish
        vector<int> assigned(matched.size(), -1);
        vector<bool> val_used(vals.size(), false);
        
        for (int i = 0; i < matched.size(); ++i) {
            int idx = matched[i];
            // Try to identify which val it is
            // We need to uniquely pinpoint.
            // Collect signatures.
            // Sig: query(u, v, idx) -> p_idx % 3.
            // If ambiguous, add query(u, v, idx, some_other_known).
            // But query size 4?
            
            // Simple approach: try to find a distinguishing query set from knowns.
            // We have knowns.
            // Try random sets of knowns of size 2. {k1, k2, idx}.
            // Check consistency.
            
            vector<int> possibilities;
            for (int j = 0; j < vals.size(); ++j) {
                if (val_used[j]) continue;
                possibilities.push_back(j);
            }
            
            // Filter possibilities
            // Use static knowns u, v.
            if (possibilities.size() > 1) {
                int res = query({u, v, idx});
                vector<int> next_poss;
                for (int pid : possibilities) {
                    int val = vals[pid];
                    bool ok = ( (1 + n + val) % 3 == 0 ) == (res == 1);
                    if (ok) next_poss.push_back(pid);
                }
                possibilities = next_poss;
            }
            
            // If still > 1, use other knowns
            int known_ptr = 0;
            vector<int> extra_knowns;
            // collect some knowns
            for (int z = 1; z <= n && extra_knowns.size() < 10; ++z) {
                if (p[z] != 0 && z != u && z != v) extra_knowns.push_back(z);
            }
            
            for (int k_idx = 0; k_idx < extra_knowns.size() && possibilities.size() > 1; ++k_idx) {
                int kz = extra_knowns[k_idx];
                int res = query({u, kz, idx});
                vector<int> next_poss;
                for (int pid : possibilities) {
                    int val = vals[pid];
                    bool ok = ( (1 + p[kz] + val) % 3 == 0 ) == (res == 1);
                    if (ok) next_poss.push_back(pid);
                }
                possibilities = next_poss;
            }
            
            if (possibilities.size() == 1) {
                int pid = possibilities[0];
                p[idx] = vals[pid];
                val_used[pid] = true;
            } else {
                // Should not happen with enough knowns or primes.
                // Just pick one
                int pid = possibilities[0];
                p[idx] = vals[pid];
                val_used[pid] = true;
            }
        }
        
        // Update current_O
        vector<int> next_O;
        for (int idx : current_O) {
            bool found = false;
            for (int m : matched) if (m == idx) found = true;
            if (!found) next_O.push_back(idx);
        }
        current_O = next_O;
        min_val_O += current_d;
        max_val_O -= current_d;
    }
    
    // Solve E (Similar)
    // Values 2, 4, ..., n.
    vector<int> current_E = E;
    int min_val_E = 2;
    int max_val_E = n;
    
    // Pre-fill knowns for E (we know u, v, and O-set)
    p[u] = 1; p[v] = n; // Assuming u=1, v=N
    // Wait, we didn't confirm u=1.
    // If we assume u=1, and consistent, fine.
    // The parity check assumes u=1.
    // If u=N, then O would be evens? No, relative parity.
    // If u=N, O has same parity as N (even). So O is Evens.
    // But we assigned min_val_O = 1 (odd).
    // If O is actually evens, we are reconstructing n+1-p?
    // Let's stick to the assumption.
    
    // Note: E might contain v (value N).
    // Our peeling logic for E should work same way.
    // But we already know v.
    // Should we remove v from E?
    // current_E initially contains v.
    // max_val_E is N.
    // peeling will find v immediately.
    // We already set p[v]=n?
    // Better to treat v as unknown inside the loop to avoid consistency issues, 
    // or set it and remove from list.
    // Let's remove knowns from lists.
    
    // Reset and do properly
    fill(p.begin(), p.end(), 0);
    p[u] = 1;
    p[v] = n;
    
    current_O.clear();
    for (int x : O) if (x != u && x != v) current_O.push_back(x);
    min_val_O = 3; 
    max_val_O = n - 1; // 1 removed
    
    // But O might contain N? No O has parity of 1. N is even.
    // N is in E.
    current_E.clear();
    for (int x : E) if (x != u && x != v) current_E.push_back(x);
    min_val_E = 2;
    max_val_E = n - 2; // N removed
    
    // Now loops
    auto solve_set = [&](vector<int>& cur_set, int min_v, int max_v) {
        while (!cur_set.empty()) {
            int k = cur_set.size();
            if (k == 0) break;
             if (k == 1) {
                p[cur_set[0]] = min_v;
                break;
            }
            
            vector<int> matched;
            for (int idx : cur_set) {
                vector<int> q;
                for (int other : cur_set) if (other != idx) q.push_back(other);
                if (query(q)) matched.push_back(idx);
            }
            
            long long d = (max_v - min_v) / (k - 1);
            vector<int> vals;
            vals.push_back(min_v);
            vals.push_back(max_v);
            if (k % 2 != 0) vals.push_back(min_v + (k - 1) / 2 * d);
            
            vector<bool> val_used(vals.size(), false);
            // Sort matched to have deterministic order? No.
            
            // Distinguish
            for (int idx : matched) {
                vector<int> poss;
                for(int j=0; j<vals.size(); ++j) if(!val_used[j]) poss.push_back(j);
                
                // Use u, v
                 if (poss.size() > 1) {
                    int res = query({u, v, idx});
                    vector<int> next;
                    for(int pid : poss) {
                         if (((1 + n + vals[pid]) % 3 == 0) == (res == 1)) next.push_back(pid);
                    }
                    poss = next;
                }
                
                // Extra knowns
                 vector<int> extra;
                 for(int z=1; z<=n && extra.size()<5; ++z) if(p[z]!=0 && z!=u && z!=v) extra.push_back(z);
                 for(int z : extra) {
                     if(poss.size() <= 1) break;
                     int res = query({u, z, idx});
                     vector<int> next;
                     for(int pid : poss) {
                         if (((1 + p[z] + vals[pid]) % 3 == 0) == (res == 1)) next.push_back(pid);
                     }
                     poss = next;
                 }
                 
                 int picked = poss[0];
                 p[idx] = vals[picked];
                 val_used[picked] = true;
            }
            
            vector<int> next_set;
            for(int idx : cur_set) {
                bool is_matched = false;
                for(int m : matched) if(m == idx) is_matched = true;
                if(!is_matched) next_set.push_back(idx);
            }
            cur_set = next_set;
            min_v += d;
            max_v -= d;
        }
    };
    
    solve_set(current_O, min_val_O, max_val_O);
    solve_set(current_E, min_val_E, max_val_E);
    
    if (p[1] > n/2) {
        for(int i=1; i<=n; ++i) p[i] = n + 1 - p[i];
    }
    
    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << p[i];
    cout << endl;

    return 0;
}