#include <bits/stdc++.h>
using namespace std;

static int n;
static vector<int> qv;

static int ask(const vector<int>& q) {
    cout << 0;
    for (int i = 1; i <= n; i++) cout << ' ' << q[i];
    cout << '\n';
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

static int find_pos1() {
    if (n == 1) return 1;

    mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());
    vector<int> cand;

    auto try_subset = [&](const vector<int>& subset, const vector<int>& complement) -> bool {
        fill(qv.begin() + 1, qv.end(), 1);
        for (int p : subset) qv[p] = 2;
        int ans = ask(qv);
        if (ans == 0) { cand = subset; return true; }        // pos1 in subset
        if (ans == 2) { cand = complement; return true; }    // pos1 in complement
        return false;
    };

    // Random half splits
    vector<int> pos(n);
    iota(pos.begin(), pos.end(), 1);
    int h = n / 2;
    for (int it = 0; it < 30 && cand.empty(); it++) {
        shuffle(pos.begin(), pos.end(), rng);
        vector<int> subset(pos.begin(), pos.begin() + h);
        vector<int> comp(pos.begin() + h, pos.end());
        if (try_subset(subset, comp)) break;
    }

    // Deterministic bit splits fallback
    if (cand.empty()) {
        int maxb = 0;
        while ((1 << maxb) <= n) maxb++;
        for (int b = 0; b <= maxb + 1 && cand.empty(); b++) {
            vector<int> subset, comp;
            subset.reserve(n);
            comp.reserve(n);
            for (int i = 1; i <= n; i++) {
                if ((i >> b) & 1) subset.push_back(i);
                else comp.push_back(i);
            }
            if (subset.empty() || comp.empty()) continue;
            if (try_subset(subset, comp)) break;
        }
    }

    if (cand.empty()) {
        // Should never happen, but avoid crash
        cand.resize(n);
        iota(cand.begin(), cand.end(), 1);
    }

    // Binary search within cand using answers 0/1
    int l = 0, r = (int)cand.size();
    while (r - l > 1) {
        int mid = (l + r) / 2;
        fill(qv.begin() + 1, qv.end(), 1);
        for (int i = l; i < mid; i++) qv[cand[i]] = 2;
        int ans = ask(qv);
        if (ans == 0) r = mid;
        else l = mid;
    }
    return cand[l];
}

static int find_pos_for_value(int val, vector<int>& rem) {
    int l = 0, r = (int)rem.size();
    while (r - l > 1) {
        int mid = (l + r) / 2;
        fill(qv.begin() + 1, qv.end(), 1);
        for (int i = l; i < mid; i++) qv[rem[i]] = val;
        int ans = ask(qv);
        if (ans == 2) r = mid;
        else l = mid;
    }
    int pos = rem[l];
    rem.erase(rem.begin() + l);
    return pos;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;
    qv.assign(n + 1, 1);

    vector<int> perm(n + 1, 0);

    if (n == 1) {
        cout << 1 << ' ' << 1 << '\n';
        cout.flush();
        return 0;
    }

    int pos1 = find_pos1();
    perm[pos1] = 1;

    vector<int> rem;
    rem.reserve(n - 1);
    for (int i = 1; i <= n; i++) if (i != pos1) rem.push_back(i);

    for (int v = 2; v <= n - 1; v++) {
        int pv = find_pos_for_value(v, rem);
        perm[pv] = v;
    }

    // Remaining position has value n
    if (!rem.empty()) perm[rem[0]] = n;

    cout << 1;
    for (int i = 1; i <= n; i++) cout << ' ' << perm[i];
    cout << '\n';
    cout.flush();
    return 0;
}