#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N;
    if (!(cin >> N)) return 0;
    vector<long long> A(N), B(N);
    for (int i = 0; i < N; ++i) cin >> A[i];
    for (int i = 0; i < N; ++i) cin >> B[i];
    long long sa = 0, sb = 0;
    for (auto x : A) sa += x;
    for (auto x : B) sb += x;
    if (sa != sb) {
        cout << "No\n";
        return 0;
    }
    // Heuristic: use adjacent operations to transform A into B when possible.
    // Necessary condition for adjacent-only: multiset of (Ai - i) equals multiset of (Bi - i).
    vector<long long> DA(N), DB(N);
    for (int i = 0; i < N; ++i) { DA[i] = A[i] - (i+1); DB[i] = B[i] - (i+1); }
    multiset<long long> msa(DA.begin(), DA.end()), msb(DB.begin(), DB.end());
    if (msa != msb) {
        cout << "No\n";
        return 0;
    }
    // Build mapping from A-items to target positions by matching DA values in order.
    unordered_map<long long, queue<int>> posB;
    posB.reserve(N*2);
    for (int i = 0; i < N; ++i) posB[DB[i]].push(i);
    vector<int> targetPos(N);
    for (int i = 0; i < N; ++i) {
        auto &q = posB[DA[i]];
        int t = q.front(); q.pop();
        targetPos[i] = t;
    }
    // Now we need to transform permutation by adjacent swaps; perform swaps and record operations (i, i+1).
    // Each adjacent operation (i, i+1) corresponds to our allowed operation with j=i+1.
    vector<pair<int,int>> ops;
    // We'll simulate moving each element to its target using bubble sort.
    vector<int> idx(N);
    iota(idx.begin(), idx.end(), 0); // current positions -> original indices
    for (int i = 0; i < N; ++i) {
        // find where the element that should go to i currently is
        int needOrig = -1;
        for (int k = 0; k < N; ++k) if (targetPos[idx[k]] == i) { needOrig = k; break; }
        for (int k = needOrig; k > i; --k) {
            // swap positions k-1 and k
            ops.emplace_back(k, k+1); // 1-based indices (k, k+1)
            swap(idx[k], idx[k-1]);
        }
    }
    // Apply the operations to A to ensure it matches B (for safety, but not necessary to output)
    vector<long long> C = A;
    for (auto &op : ops) {
        int i = op.first - 1, j = op.second - 1;
        long long ai = C[i], aj = C[j];
        C[i] = aj - 1;
        C[j] = ai + 1;
    }
    if (C != B) {
        // Should not happen if invariants hold, but guard anyway.
        cout << "No\n";
        return 0;
    }
    cout << "Yes\n";
    cout << ops.size() << "\n";
    for (auto &p : ops) cout << p.first << " " << p.second << "\n";
    return 0;
}