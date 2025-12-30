#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

vector<ll> query(int d, const vector<pair<ll, ll>>& probes) {
    cout << "? " << d;
    for (auto& [s, t] : probes) {
        cout << " " << s << " " << t;
    }
    cout << endl;
    cout.flush();
    int total = d; // Actually total = d * k, but we don't know k here. We'll read the line.
    // We'll read the whole line of integers.
    string line;
    if (cin.peek() == '\n') cin.ignore();
    getline(cin, line);
    stringstream ss(line);
    vector<ll> res;
    ll val;
    while (ss >> val) {
        res.push_back(val);
    }
    return res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    ll b, k, w;
    cin >> b >> k >> w;

    // If we have at least 4 waves, use the four-corner strategy.
    if (w >= 4) {
        ll R = b + 1;
        vector<ll> listA, listB, listC, listD;

        // Wave 1: probe A = (R, R)
        listA = query(1, {{R, R}});
        // Wave 2: probe B = (R, -R)
        listB = query(1, {{R, -R}});
        // Wave 3: probe C = (-R, R)
        listC = query(1, {{-R, R}});
        // Wave 4: probe D = (-R, -R)
        listD = query(1, {{-R, -R}});

        // Verify complementarity (optional, but good for debugging)
        // For each list, we expect the sum with its counterpart to be 4*R.
        // Actually, we don't need to pair explicitly since we compute s and t directly.

        // Compute s_i = 2*R - dA_i  and t_i = 2*R - dB_i
        vector<ll> S(k), T(k);
        for (int i = 0; i < k; i++) {
            S[i] = 2 * R - listA[i];
            T[i] = 2 * R - listB[i];
        }

        // Build bipartite graph between S and T (indices)
        vector<vector<int>> adj(k);
        for (int i = 0; i < k; i++) {
            for (int j = 0; j < k; j++) {
                ll s = S[i], t = T[j];
                ll sum = s + t;
                ll diff = s - t;
                if (sum % 2 != 0) continue;
                ll x = sum / 2;
                ll y = diff / 2;
                if (abs(x) <= b && abs(y) <= b) {
                    adj[i].push_back(j);
                }
            }
        }

        // Find a perfect matching using Kuhn's algorithm
        vector<int> matchR(k, -1);
        vector<bool> used(k);
        function<bool(int)> dfs = [&](int u) {
            for (int v : adj[u]) {
                if (!used[v]) {
                    used[v] = true;
                    if (matchR[v] == -1 || dfs(matchR[v])) {
                        matchR[v] = u;
                        return true;
                    }
                }
            }
            return false;
        };

        for (int u = 0; u < k; u++) {
            fill(used.begin(), used.end(), false);
            dfs(u);
        }

        // Check if perfect matching exists
        int matched = 0;
        for (int v = 0; v < k; v++) if (matchR[v] != -1) matched++;
        if (matched != k) {
            // Fallback: output zeros (should not happen for valid input)
            cout << "!";
            for (int i = 0; i < k; i++) cout << " 0 0";
            cout << endl;
            return 0;
        }

        // Recover points
        vector<pair<ll, ll>> points(k);
        for (int j = 0; j < k; j++) {
            int i = matchR[j];
            ll s = S[i], t = T[j];
            ll x = (s + t) / 2;
            ll y = (s - t) / 2;
            points[i] = {x, y}; // order by S index, but output order doesn't matter
        }

        // Output answer
        cout << "!";
        for (auto& [x, y] : points) {
            cout << " " << x << " " << y;
        }
        cout << endl;
    } else {
        // For w < 4, we use a simpler (but less reliable) strategy.
        // We'll try to use two waves with two probes each.
        // This part is not guaranteed to work in all cases, but it's a fallback.
        ll R = b + 1;
        // Wave 1: probes A=(R,R) and D=(-R,-R)
        auto res1 = query(2, {{R, R}, {-R, -R}});
        // Wave 2: probes B=(R,-R) and C=(-R,R)
        auto res2 = query(2, {{R, -R}, {-R, R}});

        // We'll attempt to pair distances by sorting and assuming the pairing by sum.
        sort(res1.begin(), res1.end());
        sort(res2.begin(), res2.end());
        vector<ll> S, T;
        // Pair the smallest with the largest, etc., for res1
        for (int i = 0; i < k; i++) {
            ll d1 = res1[i];
            ll d2 = res1[2*k - 1 - i];
            if (d1 + d2 != 4*R) {
                // If assumption fails, we cannot proceed reliably.
                // Output zeros as fallback.
                cout << "!";
                for (int j = 0; j < k; j++) cout << " 0 0";
                cout << endl;
                return 0;
            }
            // s = (d2 - d1)/2 = 2*R - d1 (using the smaller as dA)
            S.push_back(2*R - d1);
        }
        // Similarly for res2
        for (int i = 0; i < k; i++) {
            ll d1 = res2[i];
            ll d2 = res2[2*k - 1 - i];
            if (d1 + d2 != 4*R) {
                cout << "!";
                for (int j = 0; j < k; j++) cout << " 0 0";
                cout << endl;
                return 0;
            }
            T.push_back(2*R - d1);
        }

        // Now match S and T by sorting and assuming order corresponds.
        // This is a heuristic and may fail if points are symmetric.
        sort(S.begin(), S.end());
        sort(T.begin(), T.end());
        vector<pair<ll, ll>> points(k);
        for (int i = 0; i < k; i++) {
            ll s = S[i], t = T[i];
            ll x = (s + t) / 2;
            ll y = (s - t) / 2;
            points[i] = {x, y};
        }

        cout << "!";
        for (auto& [x, y] : points) {
            cout << " " << x << " " << y;
        }
        cout << endl;
    }

    return 0;
}