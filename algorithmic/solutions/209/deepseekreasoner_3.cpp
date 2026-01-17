#include <bits/stdc++.h>
using namespace std;
typedef long long ll;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int h;
    cin >> h;
    int n = (1 << h) - 1;
    int D = 2 * (h - 1);               // diameter
    ll L = (3 * n) / 4;                // query limit for 100 points

    // Special case for very small trees (h = 2)
    if (h == 2) {
        ll r1, r2, r3;
        cout << "? 1 1" << endl;
        cin >> r1;
        cout << "? 2 1" << endl;
        cin >> r2;
        cout << "? 3 1" << endl;
        cin >> r3;
        // Two of the responses equal f_root, the third equals f_leaf1 + f_leaf2
        ll mode;
        if (r1 == r2 || r1 == r3) mode = r1;
        else if (r2 == r3) mode = r2;
        else mode = r1;                 // fallback (should not happen)
        ll S = r1 + r2 + r3 - mode;
        cout << "! " << S << endl;
        return 0;
    }

    int total_queries = 0;
    unordered_map<int, pair<ll, ll>> data;   // u -> {B = response for d=1, sumT = sum of all distances}
    unordered_map<ll, int> freq;             // frequency of candidate sums

    // Query all distances for a given node u (if not already queried)
    auto query_node = [&](int u) {
        if (data.find(u) != data.end()) return;
        if (total_queries + D > L) return;   // respect the limit for 100 points
        ll sumT = 0, B = 0;
        for (int d = 1; d <= D; ++d) {
            cout << "? " << u << " " << d << endl;
            ll resp;
            cin >> resp;
            sumT += resp;
            if (d == 1) B = resp;
            ++total_queries;
        }
        data[u] = {B, sumT};
    };

    // Examine parent–child edges in the index tree
    for (int u = 2; u <= n; ++u) {
        int v = u / 2;   // parent of u
        bool need_u = (data.find(u) == data.end());
        bool need_v = (data.find(v) == data.end());
        int needed = (need_u ? D : 0) + (need_v ? D : 0);
        if (total_queries + needed > L) break;   // stop before exceeding the limit
        query_node(u);
        query_node(v);
        // Both nodes are now queried
        ll Bu = data[u].first, sumTu = data[u].second;
        ll Bv = data[v].first, sumTv = data[v].second;
        freq[Bu + sumTv]++;
        freq[Bv + sumTu]++;
    }

    // Find the most frequent candidate sum
    ll bestS = 0;
    int bestFreq = 0;
    for (auto &p : freq) {
        if (p.second > bestFreq) {
            bestFreq = p.second;
            bestS = p.first;
        }
    }

    // If no candidates were generated (should not happen for h>2), fallback to a simple guess
    if (bestFreq == 0) bestS = 0;

    cout << "! " << bestS << endl;
    return 0;
}