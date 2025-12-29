#include <bits/stdc++.h>
using namespace std;
using int64 = long long;

int64 gcdll(int64 a, int64 b) {
    if (a < 0) a = -a;
    if (b < 0) b = -b;
    while (b) {
        int64 t = a % b;
        a = b;
        b = t;
    }
    return a;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int Q_LIMIT = 200000;
    int64 total = 0;
    int q = 0;
    unordered_map<int,int64> first_pos;
    first_pos.reserve(300000);
    int64 G = 0;

    // Initial query to learn starting label
    cout << "walk 0" << endl;
    cout.flush();
    int label;
    if (!(cin >> label)) return 0;
    first_pos[label] = 0;
    q = 1;

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());

    while (q < Q_LIMIT) {
        int64 x = (int64)(rng() % 1000000000ULL) + 1; // 1..1e9
        cout << "walk " << x << endl;
        cout.flush();
        if (!(cin >> label)) return 0;
        ++q;
        total += x;

        auto it = first_pos.find(label);
        if (it == first_pos.end()) {
            first_pos[label] = total;
        } else {
            int64 D = total - it->second;
            if (D > 0) {
                if (G == 0) G = D;
                else G = gcdll(G, D);
            }
        }
    }

    if (G <= 0) G = 1;
    if (G > 1000000000LL) G = 1000000000LL;

    cout << "guess " << G << endl;
    cout.flush();
    return 0;
}