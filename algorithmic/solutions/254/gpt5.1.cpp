#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        if (!(cin >> n)) return 0;
        int N = n * n;

        vector<int> remaining(N);
        for (int i = 0; i < N; ++i) remaining[i] = i + 1;

        vector<int> ans;
        ans.reserve(N - n + 1);

        auto ask = [&](const vector<int>& group) -> int {
            cout << "?";
            for (int x : group) cout << ' ' << x;
            cout << '\n';
            cout.flush();
            int winner;
            if (!(cin >> winner)) exit(0);
            return winner;
        };

        auto find_max = [&](const vector<int>& S) -> int {
            vector<int> cand = S;
            vector<int> losers;
            losers.reserve(S.size());

            while (true) {
                int C = (int)cand.size();
                if (C == 1) break;
                if (C >= n) {
                    vector<int> group(n);
                    for (int i = 0; i < n; ++i) group[i] = cand[i];
                    int winner = ask(group);

                    vector<int> newCand;
                    newCand.reserve(C - n + 1);

                    for (int i = 0; i < n; ++i) {
                        if (group[i] == winner) continue;
                        losers.push_back(group[i]);
                    }
                    for (int i = n; i < C; ++i) newCand.push_back(cand[i]);
                    newCand.push_back(winner);
                    cand.swap(newCand);
                } else {
                    int need = n - C;
                    vector<int> group;
                    group.reserve(n);
                    for (int x : cand) group.push_back(x);
                    for (int i = 0; i < need; ++i) {
                        group.push_back(losers[i]);
                    }
                    int winner = ask(group);

                    vector<int> newCand;
                    newCand.reserve(1);
                    bool found = false;
                    for (int x : cand) {
                        if (x == winner) {
                            newCand.push_back(x);
                            found = true;
                        } else {
                            losers.push_back(x);
                        }
                    }
                    if (!found) {
                        newCand.clear();
                        newCand.push_back(winner);
                    }
                    cand.swap(newCand);
                    break;
                }
            }
            return cand[0];
        };

        int need = N - n + 1;
        for (int k = 0; k < need; ++k) {
            int mx = find_max(remaining);
            ans.push_back(mx);
            vector<int> newRem;
            newRem.reserve(remaining.size() - 1);
            for (int x : remaining)
                if (x != mx) newRem.push_back(x);
            remaining.swap(newRem);
        }

        cout << "!";
        for (int x : ans) cout << ' ' << x;
        cout << '\n';
        cout.flush();
    }
    return 0;
}