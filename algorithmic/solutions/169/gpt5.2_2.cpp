#include <bits/stdc++.h>
using namespace std;

struct Op {
    char d;
    int p;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;
    vector<string> C(N);
    for (int i = 0; i < N; i++) cin >> C[i];

    vector<vector<bool>> fuku(N, vector<bool>(N, false));
    vector<pair<int,int>> onis;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            if (C[i][j] == 'o') fuku[i][j] = true;
            else if (C[i][j] == 'x') onis.push_back({i, j});
        }
    }

    vector<vector<bool>> upOK(N, vector<bool>(N, false));
    vector<vector<bool>> downOK(N, vector<bool>(N, false));
    vector<vector<bool>> leftOK(N, vector<bool>(N, false));
    vector<vector<bool>> rightOK(N, vector<bool>(N, false));

    // Column-wise
    for (int j = 0; j < N; j++) {
        int pref = 0;
        for (int i = 0; i < N; i++) {
            upOK[i][j] = (pref == 0);
            if (fuku[i][j]) pref++;
        }
        int suff = 0;
        for (int i = N - 1; i >= 0; i--) {
            downOK[i][j] = (suff == 0);
            if (fuku[i][j]) suff++;
        }
    }
    // Row-wise
    for (int i = 0; i < N; i++) {
        int pref = 0;
        for (int j = 0; j < N; j++) {
            leftOK[i][j] = (pref == 0);
            if (fuku[i][j]) pref++;
        }
        int suff = 0;
        for (int j = N - 1; j >= 0; j--) {
            rightOK[i][j] = (suff == 0);
            if (fuku[i][j]) suff++;
        }
    }

    vector<Op> ops;
    ops.reserve(4 * N * N);

    auto addSeq = [&](char a, char b, int p, int k) {
        for (int t = 0; t < k; t++) ops.push_back({a, p});
        for (int t = 0; t < k; t++) ops.push_back({b, p});
    };

    for (auto [i, j] : onis) {
        int bestCost = INT_MAX;
        int bestK = 0;
        char bestA = 'U', bestB = 'D';
        int bestP = j;

        if (upOK[i][j]) {
            int k = i + 1;
            int cost = 2 * k;
            if (cost < bestCost) {
                bestCost = cost;
                bestK = k;
                bestA = 'U'; bestB = 'D';
                bestP = j;
            }
        }
        if (downOK[i][j]) {
            int k = N - i;
            int cost = 2 * k;
            if (cost < bestCost) {
                bestCost = cost;
                bestK = k;
                bestA = 'D'; bestB = 'U';
                bestP = j;
            }
        }
        if (leftOK[i][j]) {
            int k = j + 1;
            int cost = 2 * k;
            if (cost < bestCost) {
                bestCost = cost;
                bestK = k;
                bestA = 'L'; bestB = 'R';
                bestP = i;
            }
        }
        if (rightOK[i][j]) {
            int k = N - j;
            int cost = 2 * k;
            if (cost < bestCost) {
                bestCost = cost;
                bestK = k;
                bestA = 'R'; bestB = 'L';
                bestP = i;
            }
        }

        // Fallback (shouldn't happen due to guarantees)
        if (bestCost == INT_MAX) {
            int k = i + 1;
            bestK = k;
            bestA = 'U'; bestB = 'D';
            bestP = j;
        }

        addSeq(bestA, bestB, bestP, bestK);
    }

    // Safety: if something goes wrong, output nothing (always legal).
    if ((int)ops.size() > 4 * N * N) ops.clear();

    for (auto &op : ops) {
        cout << op.d << ' ' << op.p << "\n";
    }
    return 0;
}