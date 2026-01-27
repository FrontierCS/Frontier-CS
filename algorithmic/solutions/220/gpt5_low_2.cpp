#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if(!(cin >> n)) return 0;
    vector<vector<int>> cnt(n+1, vector<int>(n+1, 0));
    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < n; ++j) {
            int x; cin >> x;
            cnt[i][x]++;
        }
    }

    vector<vector<int>> ops;
    ops.reserve(n * (n - 1));

    auto mod1 = [&](int x, int m)->int{
        int r = x % m;
        if (r < 0) r += m;
        return r;
    };

    for (int round = 0; round < n; ++round) {
        for (int s = 1; s <= n-1; ++s) {
            vector<int> send(n+1, 0);
            // decide what to send
            for (int i = 1; i <= n; ++i) {
                int t = mod1(i - s - 1, n) + 1; // desired label
                if (cnt[i][t] > 0) {
                    send[i] = t;
                } else {
                    // send any available card
                    for (int v = 1; v <= n; ++v) {
                        if (cnt[i][v] > 0) {
                            send[i] = v;
                            break;
                        }
                    }
                }
            }
            // apply sending
            for (int i = 1; i <= n; ++i) {
                cnt[i][send[i]]--;
            }
            for (int i = 1; i <= n; ++i) {
                int to = (i % n) + 1;
                cnt[to][send[i]]++;
            }
            vector<int> line;
            line.reserve(n);
            for (int i = 1; i <= n; ++i) line.push_back(send[i]);
            ops.push_back(move(line));
        }
    }

    cout << ops.size() << "\n";
    for (auto &line : ops) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << line[i];
        }
        cout << "\n";
    }
    return 0;
}