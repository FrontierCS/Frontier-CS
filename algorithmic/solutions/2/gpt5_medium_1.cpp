#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<pair<int, vector<int>>> lines; // (type, sequence)
    string s;
    while (true) {
        string line;
        if (!getline(cin, line)) break;
        if (line.empty()) continue;
        stringstream ss(line);
        int t;
        if (!(ss >> t)) continue;
        vector<int> seq;
        int x;
        while (ss >> x) seq.push_back(x);
        lines.emplace_back(t, move(seq));
    }

    // Find last guess line (type 1), assume that's the hidden permutation
    int idx_last_guess = -1;
    for (int i = (int)lines.size() - 1; i >= 0; --i) {
        if (lines[i].first == 1) {
            idx_last_guess = i;
            break;
        }
    }
    if (idx_last_guess == -1) {
        // No hidden permutation provided; nothing to output
        return 0;
    }

    const vector<int>& perm = lines[idx_last_guess].second;
    int n = (int)perm.size();

    // For each query (type 0), output the count of matches with the permutation
    for (int i = 0; i < (int)lines.size(); ++i) {
        if (lines[i].first != 0) continue;
        const vector<int>& q = lines[i].second;
        int cnt = 0;
        if ((int)q.size() == n) {
            for (int j = 0; j < n; ++j) {
                if (q[j] == perm[j]) ++cnt;
            }
        }
        cout << cnt << "\n";
    }
    return 0;
}