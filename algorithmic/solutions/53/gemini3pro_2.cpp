#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

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
    if (!(cin >> n)) return;
    
    // Choose k=1.
    cout << 1 << endl;

    vector<int> p(n + 1, 0);
    vector<bool> is_target(n + 1, false);
    
    // Random generator
    mt19937 rng(1337);

    // To handle nodes that seem to be part of 2-cycles or hard to start
    vector<int> deferred;
    vector<int> nodes(n);
    iota(nodes.begin(), nodes.end(), 1);
    
    // Main loop to find chains
    // We prioritize nodes not in deferred list.
    // If we get stuck, we move node to deferred.
    
    int processed_count = 0;
    
    // We will do passes. First pass tries to solve normal cycles.
    // If stuck, defer.
    // Second pass solves deferred nodes (likely 2-cycles) by brute-force/linear scan if necessary
    // but optimized linear scan.

    vector<int> work_queue;
    for(int i=1; i<=n; ++i) work_queue.push_back(i);

    // We keep track of visited status implicitly by p[u] != 0
    
    while(processed_count < n) {
        int u = -1;
        // Find a start node
        for(int x : work_queue) {
            if (p[x] == 0) {
                u = x;
                break;
            }
        }
        if (u == -1) break; // All done

        int prev = -1; // Unknown predecessor

        // Follow chain
        while (p[u] == 0) {
            // Build candidates
            vector<int> candidates;
            for (int i = 1; i <= n; ++i) {
                if (!is_target[i] && i != u) {
                    candidates.push_back(i);
                }
            }
            
            if (candidates.empty()) break; // Should not happen

            // If prev is known, we can exclude it from S to ensure no ambiguity.
            // If prev is unknown, we use swap query.
            
            // Binary search
            while (candidates.size() > 1) {
                // If we suspect 2-cycle loop (getting 0 consistently), we might need to break out.
                // We track retry count.
                int retries = 0;
                bool progressed = false;
                
                while(retries < 5 && !progressed) {
                    int m = candidates.size();
                    int half = m / 2;
                    
                    // Shuffle for randomness if prev is unknown to avoid bad splits
                    if (prev == -1) {
                        shuffle(candidates.begin(), candidates.end(), rng);
                    }
                    
                    vector<int> S;
                    for(int i=0; i<half; ++i) S.push_back(candidates[i]);
                    
                    vector<bool> in_S(n + 1, false);
                    for(int x : S) in_S[x] = true;
                    
                    vector<int> others;
                    for(int i=1; i<=n; ++i) {
                        if (i != u && !in_S[i]) others.push_back(i);
                    }
                    
                    if (prev != -1) {
                        // Known predecessor logic
                        // Ensure prev not in S. If it is, swap S and others_part_of_candidates
                        bool prev_in_S = false;
                        for(int x : S) if(x == prev) prev_in_S = true;
                        
                        if (prev_in_S) {
                            // Swap S with complement within candidates
                            vector<int> new_S;
                            for(int x : candidates) if(!in_S[x]) new_S.push_back(x);
                            S = new_S;
                            fill(in_S.begin(), in_S.end(), false);
                            for(int x : S) in_S[x] = true;
                            others.clear();
                            for(int i=1; i<=n; ++i) if(i != u && !in_S[i]) others.push_back(i);
                        }
                        
                        // Q_active: [others, u, S]
                        vector<int> q_active = others;
                        q_active.push_back(u);
                        q_active.insert(q_active.end(), S.begin(), S.end());
                        
                        // Q_hide: [u, others, S]
                        vector<int> q_hide;
                        q_hide.push_back(u);
                        q_hide.insert(q_hide.end(), others.begin(), others.end());
                        q_hide.insert(q_hide.end(), S.begin(), S.end());
                        
                        int d = query(q_active) - query(q_hide);
                        // d = 2 => p_u in S. d = 1 => p_u not in S.
                        if (d == 2) {
                            candidates = S;
                        } else {
                            vector<int> next_cands;
                            for(int x : candidates) if(!in_S[x]) next_cands.push_back(x);
                            candidates = next_cands;
                        }
                        progressed = true;
                    } else {
                        // Unknown predecessor logic (Swap)
                        vector<int> q1 = others;
                        q1.push_back(u);
                        q1.insert(q1.end(), S.begin(), S.end());
                        
                        vector<int> q2 = others;
                        q2.insert(q2.end(), S.begin(), S.end());
                        q2.push_back(u);
                        
                        int d = query(q1) - query(q2);
                        // 1 => p_u in S
                        // -1 => p_u not in S
                        // 0 => Ambiguous
                        
                        if (d == 1) {
                            candidates = S;
                            progressed = true;
                        } else if (d == -1) {
                            vector<int> next_cands;
                            for(int x : candidates) if(!in_S[x]) next_cands.push_back(x);
                            candidates = next_cands;
                            progressed = true;
                        } else {
                            retries++;
                        }
                    }
                }
                
                if (!progressed) {
                    // Retried 5 times and got 0. Likely 2-cycle or hard case.
                    // Break out to fallback (linear scan / deferred).
                    // Since we can't narrow down, we defer this node.
                    goto defer_node;
                }
            }
            
            // Found
            {
                int target = candidates[0];
                p[u] = target;
                is_target[target] = true;
                processed_count++;
                
                if (p[target] != 0) break; // Cycle closed
                
                prev = u;
                u = target;
                continue;
            }
            
            defer_node:
            // Move u to deferred list, break chain processing
            // We will process deferred later.
            // Note: u is not solved.
            // Also need to remove u from work_queue if present?
            // Actually, we iterate work_queue. Just mark it to be skipped in main loop?
            // We can just add it to a separate list and ensure work_queue doesn't pick it again.
            // But we iterate work_queue sequentially.
            // We can move it to end of work_queue?
            break;
        }
        
        // If we broke out, pick next from queue.
    }
    
    // Process deferred / skipped nodes.
    // These are likely 2-cycles where binary search failed.
    // For 2-cycles, we can just pick a candidate v and verify u <-> v.
    // Verification: Active/Hide gives 2 if u <-> v.
    // Since we know they are 2-cycles, we iterate candidates.
    // Optimization: if we find u <-> v, we solve both.
    
    vector<int> remaining;
    for(int i=1; i<=n; ++i) if(p[i] == 0) remaining.push_back(i);
    
    for(size_t i=0; i<remaining.size(); ++i) {
        int u = remaining[i];
        if (p[u] != 0) continue;
        
        // Candidates for u
        vector<int> candidates;
        for (int j = 1; j <= n; ++j) {
            if (!is_target[j] && j != u) candidates.push_back(j);
        }
        
        // Try linear scan with Active/Hide check for 2-cycle
        // If it's a 2-cycle u <-> v, query returns 2.
        // If not, returns 1.
        for (int v : candidates) {
            // Check u -> v
            vector<int> S = {v};
            vector<int> others;
            for(int k=1; k<=n; ++k) if(k!=u && k!=v) others.push_back(k);
            
            vector<int> q_active = others;
            q_active.push_back(u);
            q_active.push_back(v);
            
            vector<int> q_hide;
            q_hide.push_back(u);
            q_hide.insert(q_hide.end(), others.begin(), others.end());
            q_hide.push_back(v);
            
            int d = query(q_active) - query(q_hide);
            if (d == 2) {
                // Found u <-> v
                p[u] = v;
                p[v] = u;
                is_target[v] = true;
                is_target[u] = true; // effectively
                processed_count += 2;
                break;
            }
        }
    }
    
    // If anything left (should not be for 2-cycles), fill randomly or by elimination?
    // Elimination is auto handled by candidates logic.
    // The last pair logic handles 2-cycles.
    // If odd chain remains? Should have been handled by BS.
    
    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << p[i];
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}