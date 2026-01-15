#include <bits/stdc++.h>
using namespace std;

const int INF = 1e9;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    cin >> t;
    while (t--) {
        int n, m;
        cin >> n >> m;
        vector<vector<int>> G(n, vector<int>(n));
        vector<int> allValues;
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                cin >> G[i][j];
                allValues.push_back(G[i][j]);
            }
        }
        sort(allValues.begin(), allValues.end()); // V[0] = smallest, V[l-1] = l-th smallest

        // precompute M[d] for d = i+j+2? Actually d = i+j, range 2..2n
        int maxD = 2 * n;
        vector<int> M(maxD + 1, INF);
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                int d = (i + 1) + (j + 1);
                M[d] = min(M[d], G[i][j]);
            }
        }

        int totalT = 2 * n - 1;
        // exact[l][T] = -1 unknown, else the queried value
        vector<vector<int>> exact(n + 1, vector<int>(totalT + 1, -1));
        // bestKey[l][T] = current best known lower bound or exact value
        vector<vector<int>> bestKey(n + 1, vector<int>(totalT + 1, INF));

        // priority queue: tuple (key, -l, T)
        using Tuple = tuple<int, int, int>;
        priority_queue<Tuple, vector<Tuple>, greater<Tuple>> pq;

        // compute initial lower bounds and push
        for (int l = 1; l <= n; ++l) {
            for (int T = 1; T <= totalT; ++T) {
                int lb;
                if (T >= l) {
                    int d_start = T - l + 2;
                    int d_end = T + 1;
                    int mx = 0;
                    for (int d = d_start; d <= d_end; ++d) {
                        mx = max(mx, M[d]);
                    }
                    lb = mx;
                } else {
                    // T < l
                    lb = allValues[l - 1]; // V[l]
                }
                bestKey[l][T] = lb;
                pq.emplace(lb, -l, T);
            }
        }

        vector<int> answers;
        int queriesMade = 0;
        while ((int)answers.size() < m) {
            auto [key, negl, T] = pq.top();
            pq.pop();
            int l = -negl;
            if (key != bestKey[l][T]) continue; // outdated entry

            if (exact[l][T] == -1) {
                // need to query
                cout << "? " << l << " " << T << endl;
                queriesMade++;
                int value;
                cin >> value;
                exact[l][T] = value;
                bestKey[l][T] = value;
                pq.emplace(value, -l, T);
            } else {
                // exact value known and this is the current bestKey -> next smallest
                answers.push_back(key);
                // mark as done by setting bestKey to INF so future pops are discarded
                bestKey[l][T] = INF;
            }
        }

        // output answer
        cout << "!";
        for (int x : answers) cout << " " << x;
        cout << endl;
    }
    return 0;
}