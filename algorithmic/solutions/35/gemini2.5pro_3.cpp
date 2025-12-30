#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <set>
#include <iterator>

using namespace std;

bool ask_query(int x, const vector<int>& S) {
    if (S.empty()) {
        return false;
    }
    cout << "? " << x << " " << S.size();
    for (int idx : S) {
        cout << " " << idx;
    }
    cout << endl;
    cout.flush();
    int response;
    cin >> response;
    if (response == -1) {
        exit(0);
    }
    return response == 1;
}

void solve() {
    int n;
    cin >> n;
    if (n == -1) {
        exit(0);
    }

    int total_indices = 2 * n - 1;

    vector<int> p_candidates(total_indices);
    iota(p_candidates.begin(), p_candidates.end(), 1);

    vector<int> v_candidates(n);
    iota(v_candidates.begin(), v_candidates.end(), 1);

    while (v_candidates.size() > 1) {
        int mid_idx = p_candidates.size() / 2;
        vector<int> p1(p_candidates.begin(), p_candidates.begin() + mid_idx);
        vector<int> p2(p_candidates.begin() + mid_idx, p_candidates.end());

        set<int> u1, u2;
        for (int x : v_candidates) {
            if (ask_query(x, p1)) {
                u1.insert(x);
            }
        }
        for (int x : v_candidates) {
            if (ask_query(x, p2)) {
                u2.insert(x);
            }
        }
        
        set<int> s11;
        std::set_intersection(u1.begin(), u1.end(),
                              u2.begin(), u2.end(),
                              std::inserter(s11, s11.begin()));

        if ((s11.size() % 2) != (p1.size() % 2)) {
            p_candidates = p1;
            vector<int> next_v_candidates;
            for (int x : u1) {
                if (s11.find(x) == s11.end()) {
                    next_v_candidates.push_back(x);
                }
            }
            v_candidates = next_v_candidates;
        } else {
            p_candidates = p2;
            vector<int> next_v_candidates;
            for (int x : u2) {
                if (s11.find(x) == s11.end()) {
                    next_v_candidates.push_back(x);
                }
            }
            v_candidates = next_v_candidates;
        }
    }
    
    cout << "! " << v_candidates[0] << endl;
    cout.flush();
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int t;
    cin >> t;
    while (t--) {
        solve();
    }

    return 0;
}