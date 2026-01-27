/**
 * Solution for Pepe Racing
 * 
 * Strategy:
 * 1. Divide N^2 pepes into N groups of N pepes.
 * 2. Find the local maximum (head) of each group.
 * 3. Maintain a set of "Heads". These are candidates for the global maximum.
 * 4. To output the next fastest pepe, we find the maximum among the current Heads.
 * 5. When a Head is removed (outputted), its group needs a new Head. We pick the next candidate from that group.
 *    However, we don't know the relative order of the remaining elements.
 *    We run a race between the remaining elements of that group and a "padding" element which is an existing Head from another group.
 *    - If the existing Head wins, the group is "blocked" by that Head (all remaining elements are slower than that Head).
 *    - If a new element wins, it becomes the new Head, and the old Head used as padding is "demoted" (put back to its group, which is then re-evaluated).
 * 6. Blocks are released when the blocking Head is outputted.
 */

#include <iostream>
#include <vector>
#include <map>
#include <queue>
#include <algorithm>

using namespace std;

int n;
int total_pepes;
int target_output;

// Interaction helper
int query(const vector<int>& v) {
    cout << "?";
    for (int x : v) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

void solve() {
    if (!(cin >> n)) return;
    total_pepes = n * n;
    target_output = total_pepes - n + 1;

    // U[i] stores the un-outputted, non-head pepes of group i
    vector<vector<int>> U(n + 1);
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            U[i].push_back((i - 1) * n + j);
        }
    }

    map<int, int> heads; // group_id -> pepe_id
    map<int, int> head_to_group; // pepe_id -> group_id
    // blocked_by[p] stores list of groups blocked by pepe p
    vector<vector<int>> blocked_by(total_pepes + 1);
    queue<int> pending;

    // Initialization: find initial head for each group
    for (int i = 1; i <= n; ++i) {
        int w = query(U[i]);
        vector<int> next_U;
        next_U.reserve(n);
        for(int x : U[i]) if(x != w) next_U.push_back(x);
        U[i] = next_U;
        
        heads[i] = w;
        head_to_group[w] = i;
    }

    vector<int> result;
    result.reserve(total_pepes);
    int result_count = 0;

    while (result_count < target_output) {
        // Phase A: Resolve Pending groups (groups needing a head)
        while (!pending.empty()) {
            int g = pending.front();
            
            if (U[g].empty()) {
                pending.pop();
                continue;
            }
            
            // We need a padding element to compare against. Use an existing head.
            if (heads.empty()) break; 

            int p_pepe = heads.begin()->second;
            int p_group = heads.begin()->first;

            vector<int> q;
            q.reserve(n);
            for(int x : U[g]) q.push_back(x);
            // U[g] has size n-1, so we add 1 padding element
            q.push_back(p_pepe);

            int w = query(q);

            if (w == p_pepe) {
                // The padding head wins. Group g is blocked by p_pepe.
                blocked_by[p_pepe].push_back(g);
                pending.pop();
            } else {
                // A new element w from group g wins. w > p_pepe.
                // Promote w to head of g.
                vector<int> next_U_g;
                next_U_g.reserve(n);
                for(int x : U[g]) if(x != w) next_U_g.push_back(x);
                U[g] = next_U_g;

                heads[g] = w;
                head_to_group[w] = g;
                pending.pop();

                // Demote p_pepe: remove from heads, return to its group, mark group pending.
                heads.erase(p_group);
                head_to_group.erase(p_pepe);
                
                U[p_group].push_back(p_pepe);
                pending.push(p_group);
            }
        }

        // Phase B: Find Global Max among current Heads
        vector<int> candidates;
        for(auto const& [grp, id] : heads) {
            candidates.push_back(id);
        }
        
        int best = -1;
        if (candidates.empty()) {
            break;
        } else if (candidates.size() == 1) {
            best = candidates[0];
        } else {
            vector<int> q = candidates;
            // Pad if necessary to reach size n
            if ((int)q.size() < n) {
                for (int i = 1; i <= n; ++i) {
                    if ((int)q.size() == n) break;
                    for (int x : U[i]) {
                        q.push_back(x);
                        if ((int)q.size() == n) break;
                    }
                }
            }
            best = query(q);
        }

        result.push_back(best);
        result_count++;

        int best_grp = head_to_group[best];
        heads.erase(best_grp);
        head_to_group.erase(best);

        // Calculate new head for best_grp
        pending.push(best_grp);

        // Release groups blocked by the outputted pepe
        for (int b_grp : blocked_by[best]) {
            pending.push(b_grp);
        }
        blocked_by[best].clear(); 
    }

    cout << "!";
    for (int x : result) cout << " " << x;
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}