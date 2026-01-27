#include <bits/stdc++.h>
using namespace std;

struct Op {
    int u, c, v;
};

static long long compute_cost(int n, int B) {
    int M = n / B + 1; // block starts: 0, B, 2B, ..., floor(n/B)*B
    long long intra = 0;
    for (int i = 0; i < M; i++) {
        int L = i * B;
        int R = min(n, (i + 1) * B - 1);
        int s = R - L + 1;
        if (s >= 2) intra += 1LL * (s - 1) * (s - 2) / 2; // all non-consecutive edges inside block
    }
    long long startEdges = 1LL * M * (M - 1) / 2; // complete DAG among block starts
    long long nextEdges = 0; // internal vertices -> next block start
    if (M >= 2 && B >= 3) nextEdges = 1LL * (M - 1) * (B - 2);
    return intra + startEdges + nextEdges;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n <= 3) {
        cout << 0 << "\n";
        return 0;
    }

    int N = n + 1;

    int bestB = 2;
    long long bestCost = LLONG_MAX;
    for (int B = 2; B <= N; B++) {
        long long c = compute_cost(n, B);
        if (c < bestCost) {
            bestCost = c;
            bestB = B;
        }
    }

    int B = bestB;
    vector<int> starts;
    for (int s = 0; s <= n; s += B) starts.push_back(s);
    int M = (int)starts.size();

    vector<Op> ops;
    ops.reserve((size_t)bestCost + 16);

    // 1) Make each block a complete DAG (add all edges with length >= 2 inside the block)
    for (int idx = 0; idx < M; idx++) {
        int L = starts[idx];
        int R = (idx + 1 < M ? min(n, L + B - 1) : n);
        int s = R - L + 1;
        for (int d = 2; d <= s - 1; d++) {
            for (int u = L; u + d <= R; u++) {
                int v = u + d;
                int c = v - 1;
                ops.push_back({u, c, v});
            }
        }
    }

    // 2) Add edges between adjacent block starts: start -> nextStart using intermediate (nextStart-1)
    for (int idx = 0; idx + 1 < M; idx++) {
        int u = starts[idx];
        int v = starts[idx + 1];
        int c = v - 1;
        ops.push_back({u, c, v});
    }

    // 3) Complete DAG among block starts via DP on distance
    for (int dist = 2; dist <= M - 1; dist++) {
        for (int i = 0; i + dist < M; i++) {
            int u = starts[i];
            int v = starts[i + dist];
            int c = starts[i + dist - 1];
            ops.push_back({u, c, v});
        }
    }

    // 4) For internal vertices of each full block, add edge to next block start via block end
    for (int idx = 0; idx + 1 < M; idx++) {
        int L = starts[idx];
        int next = starts[idx + 1];
        int R = next - 1;
        int c = R;
        for (int u = L + 1; u <= R - 1; u++) {
            ops.push_back({u, c, next});
        }
    }

    cout << ops.size() << "\n";
    for (auto &op : ops) {
        cout << op.u << ' ' << op.c << ' ' << op.v << "\n";
    }
    return 0;
}