#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cassert>

using namespace std;

int n;
const int K = 1; // Choose a fixed k. 1 is as good as any.

// Query the interactive judge
int do_query(const vector<int>& q) {
    cout << "?";
    for (int x : q) {
        cout << " " << x;
    }
    cout << endl;
    int result;
    cin >> result;
    if (result == -1) exit(0);
    return result;
}

// Get I(p[u] in S) - I(p[v] in S), where p[v]=u
int get_diff(int u, int v, const vector<int>& S) {
    if (S.empty()) {
        return 0;
    }

    vector<bool> in_S(n + 1, false);
    for (int s_val : S) {
        in_S[s_val] = true;
    }

    // Base permutation with u and v at specific positions
    vector<int> q_base;
    q_base.push_back(u);
    q_base.push_back(v);
    for (int i = 1; i <= n; ++i) {
        if (i != u && i != v) {
            q_base.push_back(i);
        }
    }

    // q1: u is at k, S is right after v.
    // We want to check pairs (i, j) where i != k.
    // Let's place u at position k, and S after v.
    vector<int> q1(n);
    vector<bool> used(n + 1, false);
    
    q1[K-1] = u; used[u] = true;
    
    int current_pos = 0;
    auto place_next = [&](int val) {
        while(q1[current_pos] != 0) current_pos++;
        q1[current_pos] = val;
        used[val] = true;
    };

    place_next(v);
    for(int s_val : S) place_next(s_val);
    for(int i = 1; i <= n; ++i) if(!used[i]) place_next(i);
    
    // q2: u is at k, S is before v.
    vector<int> q2(n);
    fill(used.begin(), used.end(), false);

    q2[K-1] = u; used[u] = true;

    current_pos = 0;
    auto place_next2 = [&](int val) {
        while(q2[current_pos] != 0) current_pos++;
        q2[current_pos] = val;
        used[val] = true;
    };
    
    for(int s_val : S) place_next2(s_val);
    place_next2(v);
    for(int i = 1; i <= n; ++i) if(!used[i]) place_next2(i);

    return do_query(q1) - do_query(q2);
}


void solve() {
    cin >> n;
    cout << K << endl;

    vector<int> p(n + 1, 0);
    vector<bool> found(n + 1, false);

    for (int i = 1; i <= n; ++i) {
        if (found[i]) {
            continue;
        }

        vector<int> cycle;
        int start_node = i;
        int curr = i;

        while (!found[curr]) {
            cycle.push_back(curr);
            found[curr] = true;

            vector<int> candidates;
            for (int j = 1; j <= n; ++j) {
                if (!found[j]) {
                    candidates.push_back(j);
                }
            }
            if (candidates.empty()) {
                p[curr] = start_node;
                curr = start_node;
                break;
            }
            if (candidates.size() == 1) {
                p[curr] = candidates[0];
                curr = candidates[0];
                continue;
            }
            
            // For the first element, we don't know predecessor.
            // Find p[curr] by checking against all candidates.
            // This is slow, but we only do it for the first element of each cycle.
            int next_val = -1;
            int last_cand = candidates.back();
            candidates.pop_back();

            int diff = get_diff(curr, last_cand, candidates);
            
            // If p[curr] is in candidates, diff will be 1.
            if (diff == 1) { 
                 int l = 0, r = candidates.size() - 1;
                 while(l < r) {
                    int mid = l + (r - l) / 2;
                    vector<int> S;
                    for (int k = l; k <= mid; ++k) S.push_back(candidates[k]);
                    if (get_diff(curr, last_cand, S) == 1) {
                        r = mid;
                    } else {
                        l = mid + 1;
                    }
                 }
                 next_val = candidates[l];
            } else {
                 next_val = last_cand;
            }

            p[curr] = next_val;
            curr = next_val;
        }
    }

    cout << "!";
    for (int j = 1; j <= n; ++j) {
        cout << " " << p[j];
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.flush();
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}