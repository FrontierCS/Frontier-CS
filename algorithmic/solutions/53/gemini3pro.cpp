#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Helper to perform a query
int query(const vector<int>& q) {
    cout << "?";
    for (int x : q) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

void solve() {
    int n;
    cin >> n;
    // We choose k = n. This means we essentially count all pairs (i, j) with i < j
    // since i can never be n in a valid pair (i, j).
    cout << n << endl;

    vector<int> p(n + 1);
    vector<bool> visited(n + 1, false);   // if node has been processed as source
    
    // available targets. Initially all 1..n are potential targets.
    vector<int> available(n);
    iota(available.begin(), available.end(), 1);

    // Process each connected component (cycle)
    for (int start_node = 1; start_node <= n; ++start_node) {
        if (visited[start_node]) continue;

        int curr = start_node;
        while (true) {
            visited[curr] = true;
            
            // Prepare candidates: available targets excluding curr
            // curr cannot be p[curr] (problem statement)
            vector<int> cand;
            cand.reserve(available.size());
            for(int x : available) {
                if(x != curr) cand.push_back(x);
            }

            int target = -1;

            if (cand.size() == 1) {
                target = cand[0];
            } else {
                // Iteratively narrow down candidates
                vector<int> current_cand = cand;
                
                while (current_cand.size() > 1) {
                    // Identify "others": all nodes except curr and current_cand
                    // These will serve as padding to keep relative positions stable
                    vector<int> others;
                    vector<bool> is_active(n + 1, false);
                    is_active[curr] = true;
                    for(int x : current_cand) is_active[x] = true;
                    for (int i = 1; i <= n; ++i) {
                        if (!is_active[i]) others.push_back(i);
                    }

                    if (current_cand.size() == 2) {
                        int c1 = current_cand[0];
                        int c2 = current_cand[1];
                        
                        // Construct two queries to distinguish c1 and c2
                        // q_yes: others + curr + c1 + c2
                        // q_no:  others + c1 + curr + c2
                        vector<int> q_yes = others; 
                        q_yes.push_back(curr); q_yes.push_back(c1); q_yes.push_back(c2);
                        
                        vector<int> q_no = others; 
                        q_no.push_back(c1); q_no.push_back(curr); q_no.push_back(c2);
                        
                        int r1 = query(q_yes);
                        int r2 = query(q_no);
                        
                        // If p[curr] == c1, then in q_yes we have (curr, c1) edge (count 1)
                        // In q_no we have (c1, curr) edge (count 0, since p[c1] != curr is guaranteed effectively or doesn't matter)
                        // Actually, diff is [p[curr]==c1] - [p[c1]==curr]. 
                        // We know p[c1] != curr is not guaranteed? 
                        // Wait, previous node is p^-1[curr]. Since we follow cycle, p^-1[curr] is 'prev'.
                        // 'prev' is already visited and removed from available.
                        // c1 is in available, so c1 != prev. So p[c1] != curr.
                        // So diff is exactly 1 if p[curr] == c1, else 0 (if p[curr] == c2).
                        
                        if (r1 - r2 == 1) {
                            current_cand = {c1};
                        } else {
                            current_cand = {c2};
                        }
                    } else {
                        // Ternary split
                        int sz = current_cand.size();
                        int s1_sz = (sz + 2) / 3;
                        int s2_sz = (sz - s1_sz + 1) / 2;
                        
                        vector<int> S1, S2, S3;
                        for(int i=0; i<sz; ++i) {
                            if(i < s1_sz) S1.push_back(current_cand[i]);
                            else if(i < s1_sz + s2_sz) S2.push_back(current_cand[i]);
                            else S3.push_back(current_cand[i]);
                        }
                        
                        // Re-build active set parts for clarity
                        vector<int> U = {curr};
                        
                        // Helper to build full query
                        auto build = [&](const vector<int>& p1, const vector<int>& p2, const vector<int>& p3, const vector<int>& p4) {
                            vector<int> q = others;
                            q.insert(q.end(), p1.begin(), p1.end());
                            q.insert(q.end(), p2.begin(), p2.end());
                            q.insert(q.end(), p3.begin(), p3.end());
                            q.insert(q.end(), p4.begin(), p4.end());
                            return q;
                        };
                        
                        // q0: others + S1 + S2 + u + S3
                        // q1: others + u + S1 + S2 + S3
                        // q2: others + S1 + u + S2 + S3
                        vector<int> q0 = build(S1, S2, U, S3);
                        vector<int> q1 = build(U, S1, S2, S3);
                        vector<int> q2 = build(S1, U, S2, S3);
                        
                        int r1 = query(q1);
                        int r2 = query(q2);
                        
                        if (r1 - r2 == 1) {
                            current_cand = S1;
                        } else {
                            int r0 = query(q0);
                            if (r2 - r0 == 1) {
                                current_cand = S2;
                            } else {
                                current_cand = S3;
                            }
                        }
                    }
                }
                target = current_cand[0];
            }
            
            p[curr] = target;
            
            // Remove target from available
            for(size_t i=0; i<available.size(); ++i) {
                if(available[i] == target) {
                    available.erase(available.begin() + i);
                    break;
                }
            }
            
            if (visited[target]) break; // cycle closed
            curr = target;
        }
    }
    
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