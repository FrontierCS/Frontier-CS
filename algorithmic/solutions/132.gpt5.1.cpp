#include <bits/stdc++.h>
using namespace std;

struct Entry {
    uint64_t key;
    unsigned short a;
    unsigned short b;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int R, H;
    if (!(cin >> R >> H)) return 0;

    const int N = 1000;
    int T = min(R, 63);                 // number of robots/tests we actually use
    uint64_t mask = (T == 64) ? ~0ULL : ((1ULL << T) - 1);

    mt19937_64 rng(123456789);

    vector<uint64_t> code(N + 1);
    long long pairs = 1LL * N * (N + 1) / 2;
    vector<Entry> arr;
    arr.reserve((size_t)pairs);

    // Generate codes until the OR of all pairs is injective
    while (true) {
        for (int i = 1; i <= N; ++i) {
            code[i] = rng() & mask;
        }

        arr.clear();
        for (int i = 1; i <= N; ++i) {
            uint64_t ci = code[i];
            for (int j = i; j <= N; ++j) {
                uint64_t key = ci | code[j];
                arr.push_back({key, (unsigned short)i, (unsigned short)j});
            }
        }

        sort(arr.begin(), arr.end(), [](const Entry &x, const Entry &y) {
            return x.key < y.key;
        });

        bool ok = true;
        for (size_t i = 1; i < arr.size(); ++i) {
            if (arr[i].key == arr[i - 1].key) {
                ok = false;
                break;
            }
        }
        if (ok) break;
    }

    // Prepare queries for each test bit
    vector<vector<int>> queries(T);
    for (int pos = 1; pos <= N; ++pos) {
        uint64_t v = code[pos];
        for (int bit = 0; bit < T; ++bit) {
            if (v & (1ULL << bit)) queries[bit].push_back(pos);
        }
    }

    // Send all queries
    for (int bit = 0; bit < T; ++bit) {
        const auto &v = queries[bit];
        cout << "? " << v.size();
        for (int x : v) cout << ' ' << x;
        cout << '\n';
        cout.flush();
    }

    // Get all answers
    cout << "@\n";
    cout.flush();

    int L;
    if (!(cin >> L)) return 0;
    vector<int> ans(L);
    for (int i = 0; i < L; ++i) cin >> ans[i];

    uint64_t pattern = 0;
    int limit = min(L, T);
    for (int i = 0; i < limit; ++i) {
        if (ans[i]) pattern |= (1ULL << i);
    }
    pattern &= mask;

    // Decode pattern via binary search in sorted array
    int lo = 0, hi = (int)arr.size() - 1;
    unsigned short a = 1, b = 1;
    bool found = false;
    while (lo <= hi) {
        int mid = (lo + hi) >> 1;
        if (arr[mid].key == pattern) {
            a = arr[mid].a;
            b = arr[mid].b;
            found = true;
            break;
        } else if (arr[mid].key < pattern) {
            lo = mid + 1;
        } else {
            hi = mid - 1;
        }
    }

    if (!found) {
        a = 1;
        b = 1;
    }

    cout << "! " << (int)a << ' ' << (int)b << '\n';
    cout.flush();

    return 0;
}