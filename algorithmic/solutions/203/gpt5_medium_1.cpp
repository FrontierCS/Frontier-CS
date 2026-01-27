#include <bits/stdc++.h>
using namespace std;

int query(const vector<int>& S) {
    cout << "Query " << S.size();
    for (int x : S) cout << " " << x;
    cout << endl;
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    vector<int> unmatched;
    vector<pair<int,int>> answers;

    for (int x = 1; x <= 2*N; ++x) {
        vector<int> U = unmatched;
        U.push_back(x);
        int r = query(U);
        if (r == (int)unmatched.size() + 1) {
            // Mate not in unmatched; add x to unmatched
            unmatched.push_back(x);
        } else {
            // Mate is in unmatched; locate by binary search
            vector<int> S = unmatched;
            while (S.size() > 1) {
                int half = (int)S.size() / 2;
                vector<int> A(S.begin(), S.begin() + half);
                vector<int> Ua = A;
                Ua.push_back(x);
                int ra = query(Ua);
                if (ra == (int)A.size()) {
                    // Mate is in A
                    S = A;
                } else {
                    // Mate in S \ A
                    S.erase(S.begin(), S.begin() + half);
                }
            }
            int mate = S[0];
            answers.emplace_back(x, mate);
            // Remove mate from unmatched
            auto it = find(unmatched.begin(), unmatched.end(), mate);
            if (it != unmatched.end()) unmatched.erase(it);
        }
    }

    for (auto &p : answers) {
        cout << "Answer " << p.first << " " << p.second << endl;
        cout.flush();
    }

    return 0;
}