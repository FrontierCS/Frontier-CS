#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

int n;
vector<int> p; // Stores the permutation, 1-based. 0 means unknown.
vector<int> known_indices; // Stores indices where p is known.

int ask(const vector<int>& q) {
    cout << "0";
    for (int x : q) {
        cout << " " << x;
    }
    cout << endl;
    int res;
    cin >> res;
    return res;
}

void guess(const vector<int>& ans) {
    cout << "1";
    for (int i = 0; i < n; ++i) {
        cout << " " << ans[i];
    }
    cout << endl;
    exit(0);
}

// Find position of val among candidates.
// pad_val is used for candidates not in the current test half.
// It is assumed pad_val does not match any value in candidates.
int solve_single(int val, vector<int>& candidates, int pad_val) {
    int l = 0, r = candidates.size() - 1;
    while (l < r) {
        int mid = l + (r - l) / 2;
        vector<int> q(n);
        // Fill query
        // Default to pad_val for unknown positions
        for (int i = 1; i <= n; ++i) {
            if (p[i] != 0) q[i-1] = p[i];
            else q[i-1] = pad_val;
        }
        
        // Set first half candidates to val
        for (int i = l; i <= mid; ++i) {
            q[candidates[i]-1] = val;
        }
        
        int score = ask(q);
        
        // Calculate expected score from known positions
        int expected = 0;
        for (int idx : known_indices) {
            // p[idx] is known. q[idx-1] is set to p[idx].
            expected++;
        }
        
        // If score > expected, then val is in the first half
        // The only way score exceeds expected is if val matched at one of the candidates in [l, mid]
        if (score > expected) {
            r = mid;
        } else {
            l = mid + 1;
        }
    }
    return candidates[l];
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> n)) return 0;
    
    p.assign(n + 1, 0);
    
    if (n == 1) {
        guess({1});
    }
    
    // Step 1: Find 1 and 2
    // We need to separate 1 and 2 into two sets
    vector<int> candidates(n);
    iota(candidates.begin(), candidates.end(), 1);
    
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    vector<int> u1, u2;
    while (true) {
        shuffle(candidates.begin(), candidates.end(), rng);
        int mid = n / 2;
        u1.clear(); u2.clear();
        vector<int> q(n);
        for (int i = 0; i < n; ++i) {
            if (i < mid) {
                u1.push_back(candidates[i]);
                q[candidates[i]-1] = 1;
            } else {
                u2.push_back(candidates[i]);
                q[candidates[i]-1] = 2;
            }
        }
        
        int score = ask(q);
        if (score == 2) {
            // 1 in u1, 2 in u2
            break;
        } else if (score == 0) {
            // 1 in u2, 2 in u1
            swap(u1, u2);
            break;
        }
        // score 1: try again
    }
    
    int pos1 = solve_single(1, u1, 2);
    p[pos1] = 1;
    known_indices.push_back(pos1);
    
    int pos2 = solve_single(2, u2, 1);
    p[pos2] = 2;
    known_indices.push_back(pos2);
    
    // Step 2: Find 3..n
    vector<int> unknowns;
    for (int i = 1; i <= n; ++i) {
        if (p[i] == 0) unknowns.push_back(i);
    }
    
    for (int k = 3; k <= n; ++k) {
        // If only one unknown left, it must be k
        if (unknowns.size() == 1) {
            p[unknowns[0]] = k;
            known_indices.push_back(unknowns[0]);
            unknowns.clear();
            break;
        }
        
        int pos = solve_single(k, unknowns, 1);
        p[pos] = k;
        known_indices.push_back(pos);
        
        for (int i = 0; i < unknowns.size(); ++i) {
            if (unknowns[i] == pos) {
                unknowns.erase(unknowns.begin() + i);
                break;
            }
        }
    }
    
    vector<int> ans;
    for (int i = 1; i <= n; ++i) ans.push_back(p[i]);
    guess(ans);
    
    return 0;
}