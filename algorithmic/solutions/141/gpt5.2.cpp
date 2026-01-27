#include <bits/stdc++.h>
using namespace std;

static int n, kcap;
static int ops = 0;

static bool ask(int c) {
    cout << "? " << c << "\n";
    cout.flush();
    char ans;
    if (!(cin >> ans)) exit(0);
    ++ops;
    return ans == 'Y';
}

static void resetMem() {
    cout << "R\n";
    cout.flush();
    ++ops;
}

static bool isDuplicate(int idx, const vector<int>& reps) {
    int m = (int)reps.size();
    if (m == 0) return false;

    resetMem();

    if (m <= kcap) {
        for (int r : reps) (void)ask(r);
        return ask(idx);
    }

    // m > kcap
    int fullGroups = m / kcap;
    int rem = m % kcap;

    // Process full groups without resetting in between: each group uses exactly kcap rep queries,
    // guaranteeing idx is evicted before each membership check.
    for (int g = 0; g < fullGroups; g++) {
        int start = g * kcap;
        for (int t = 0; t < kcap; t++) (void)ask(reps[start + t]);
        if (ask(idx)) return true;
    }

    if (rem == 0) return false;

    // Last partial group: either pad to kcap or do an extra reset (cheaper when rem is small).
    int start = fullGroups * kcap;
    if (1 + rem < kcap) {
        resetMem();
        for (int t = 0; t < rem; t++) (void)ask(reps[start + t]);
        return ask(idx);
    } else {
        for (int t = 0; t < rem; t++) (void)ask(reps[start + t]);
        for (int t = rem; t < kcap; t++) (void)ask(reps[0]);
        return ask(idx);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> kcap)) return 0;

    vector<int> reps;
    reps.reserve(n);

    for (int i = 1; i <= n; i++) {
        bool dup = isDuplicate(i, reps);
        if (!dup) reps.push_back(i);
    }

    cout << "! " << (int)reps.size() << "\n";
    cout.flush();
    return 0;
}