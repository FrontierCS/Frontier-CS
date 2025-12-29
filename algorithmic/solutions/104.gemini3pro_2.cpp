#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;

// Weights for states 0, 1, 2, 3, 4
// 0: Neutral, 1: H, 2: HH, 3: D, 4: DD
// Weights chosen to ensure potential reduction factor aligns with problem constraints.
const int W[5] = {4, 3, 2, 3, 2};

void solve() {
    int n;
    if (!(cin >> n)) return;

    // cands[s] stores the list of student roll numbers currently in state s
    vector<int> cands[5];
    cands[0].reserve(n);
    for (int i = 1; i <= n; ++i) cands[0].push_back(i);

    int total_cands = n;
    int max_queries = 2 * (int)ceil(log(n) / log(1.116));
    int queries_count = 0;

    // Continue querying until we have narrowed down to at most 2 candidates
    // or we run out of queries (though the strategy should be efficient enough)
    while (total_cands > 2 && queries_count < max_queries) {
        // We want to determine a split value v such that querying range [1, v]
        // minimizes the maximum potential of the next state.
        
        int tot[5];
        for(int i=0; i<5; ++i) tot[i] = cands[i].size();

        int cur[5] = {0, 0, 0, 0, 0}; // Count of candidates <= current value
        int idx[5] = {0, 0, 0, 0, 0}; // Iterators for the sorted lists
        
        long long best_score = -1;
        int best_v = -1;

        // Iterate through all candidate positions in sorted order
        while(true) {
            // Find the smallest value pointed to by the iterators
            int min_val = 2000000000;
            for(int i=0; i<5; ++i) {
                if(idx[i] < tot[i]) {
                    if(cands[i][idx[i]] < min_val) min_val = cands[i][idx[i]];
                }
            }
            if(min_val == 2000000000) break;

            // Advance pointers for all lists containing min_val
            for(int i=0; i<5; ++i) {
                if(idx[i] < tot[i] && cands[i][idx[i]] == min_val) {
                    cur[i]++;
                    idx[i]++;
                }
            }
            
            // Calculate potential for split at min_val (inclusive)
            // If query is [1, v]:
            // Candidates <= v are IN (cur[i])
            // Candidates > v are OUT (tot[i] - cur[i])
            
            // Potential if Response is 0 (Inside):
            // IN -> Honest, OUT -> Dishonest
            long long pot0 = 0;
            pot0 += (long long)cur[0] * W[1] + (long long)(tot[0] - cur[0]) * W[3]; // 0->1, 0->3
            pot0 += (long long)cur[1] * W[2] + (long long)(tot[1] - cur[1]) * W[3]; // 1->2, 1->3
            pot0 += (long long)cur[2] * 0    + (long long)(tot[2] - cur[2]) * W[3]; // 2->Dead, 2->3
            pot0 += (long long)cur[3] * W[1] + (long long)(tot[3] - cur[3]) * W[4]; // 3->1, 3->4
            pot0 += (long long)cur[4] * W[1] + (long long)(tot[4] - cur[4]) * 0;    // 4->1, 4->Dead
            
            // Potential if Response is 1 (Outside):
            // IN -> Dishonest, OUT -> Honest
            long long pot1 = 0;
            pot1 += (long long)cur[0] * W[3] + (long long)(tot[0] - cur[0]) * W[1]; // 0->3, 0->1
            pot1 += (long long)cur[1] * W[3] + (long long)(tot[1] - cur[1]) * W[2]; // 1->3, 1->2
            pot1 += (long long)cur[2] * W[3] + (long long)(tot[2] - cur[2]) * 0;    // 2->3, 2->Dead
            pot1 += (long long)cur[3] * W[4] + (long long)(tot[3] - cur[3]) * W[1]; // 3->4, 3->1
            pot1 += (long long)cur[4] * 0    + (long long)(tot[4] - cur[4]) * W[1]; // 4->Dead, 4->1
            
            long long score = max(pot0, pot1);
            if(best_score == -1 || score < best_score) {
                best_score = score;
                best_v = min_val;
            }
        }
        
        // Ask the query
        cout << "? 1 " << best_v << endl;
        queries_count++;
        int ans;
        cin >> ans;
        
        // Determine if response implies Inside or Outside
        // Range length is best_v.
        // If ans == best_v, it is "Outside" type response (Honest->Out, Dishonest->In)
        // If ans == best_v - 1, it is "Inside" type response (Honest->In, Dishonest->Out)
        int resp_type = (ans == best_v) ? 1 : 0;
        
        vector<int> next_cands[5];
        
        for(int s=0; s<5; ++s) {
            for(int x : cands[s]) {
                bool is_in = (x <= best_v);
                int next_s = -1;
                
                if (resp_type == 0) { // Response: Inside (count = len-1)
                    if (is_in) { // Implies Honest
                         if(s==0) next_s=1;
                         else if(s==1) next_s=2;
                         else if(s==2) next_s=-1; // Dead
                         else if(s==3) next_s=1;
                         else if(s==4) next_s=1;
                    } else { // Implies Dishonest
                         if(s==0) next_s=3;
                         else if(s==1) next_s=3;
                         else if(s==2) next_s=3;
                         else if(s==3) next_s=4;
                         else if(s==4) next_s=-1; // Dead
                    }
                } else { // Response: Outside (count = len)
                    if (is_in) { // Implies Dishonest
                         if(s==0) next_s=3;
                         else if(s==1) next_s=3;
                         else if(s==2) next_s=3;
                         else if(s==3) next_s=4;
                         else if(s==4) next_s=-1; // Dead
                    } else { // Implies Honest
                         if(s==0) next_s=1;
                         else if(s==1) next_s=2;
                         else if(s==2) next_s=-1; // Dead
                         else if(s==3) next_s=1;
                         else if(s==4) next_s=1;
                    }
                }
                
                if(next_s != -1) {
                    next_cands[next_s].push_back(x);
                }
            }
        }
        
        total_cands = 0;
        for(int i=0; i<5; ++i) {
            cands[i] = next_cands[i];
            sort(cands[i].begin(), cands[i].end());
            total_cands += cands[i].size();
        }
    }

    // Collect remaining candidates
    vector<int> final_list;
    for(int i=0; i<5; ++i) {
        for(int x : cands[i]) final_list.push_back(x);
    }
    sort(final_list.begin(), final_list.end());
    final_list.erase(unique(final_list.begin(), final_list.end()), final_list.end());

    // Guess
    for (int x : final_list) {
        cout << "! " << x << endl;
        int y;
        cin >> y;
        if (y == 1) break;
    }
    cout << "#" << endl;
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