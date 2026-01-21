#include <bits/stdc++.h>
using namespace std;

mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());
const int Q_LIMIT = 4269;

int ask(int i, int j) {
    cout << "? " << i << " " << j << '\n';
    cout.flush();
    int x;
    if (!(cin >> x)) exit(0);
    if (x == -1) exit(0);
    return x;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int B = 0;
    while ((1 << B) < n) ++B;
    int ALL = (1 << B) - 1;

    vector<int> approx(n + 1, ALL);
    int queries = 0;

    // Stage 1: two rounds of random pairings
    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 1);
    int rounds = 2;
    for (int r = 0; r < rounds; ++r) {
        shuffle(idx.begin(), idx.end(), rng);
        for (int k = 0; k + 1 < n; k += 2) {
            int i = idx[k];
            int j = idx[k + 1];
            int x = ask(i, j);
            ++queries;
            approx[i] &= x;
            approx[j] &= x;
        }
    }

    int budgetForStage2 = n - 1;
    int restBudget = Q_LIMIT - queries - budgetForStage2;
    if (restBudget < 0) restBudget = 0;

    int desired_m = 14;
    int maxK = min(12, n);
    int K;
    if (restBudget >= desired_m) {
        K = min(maxK, restBudget / desired_m);
    } else {
        K = 1;
        desired_m = restBudget;
    }
    if (desired_m < 0) desired_m = 0;
    if (K < 1) K = 1;

    // Candidate indices: top K by approx value
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);
    sort(order.begin(), order.end(), [&](int a, int b) {
        if (approx[a] != approx[b]) return approx[a] < approx[b];
        return a < b;
    });

    K = min(K, n);
    vector<int> cand(order.begin(), order.begin() + K);

    int zero_index = -1;

    // Stage 1.5: refine candidates
    for (int id = 0; id < K; ++id) {
        if (queries >= Q_LIMIT - budgetForStage2) break;
        int i = cand[id];
        for (int t = 0; t < desired_m && approx[i] != 0; ++t) {
            if (queries >= Q_LIMIT - budgetForStage2) break;
            int j = rng() % n + 1;
            while (j == i) j = rng() % n + 1;
            int x = ask(i, j);
            ++queries;
            approx[i] &= x;
        }
        if (approx[i] == 0) {
            zero_index = i;
            break;
        }
    }

    if (zero_index == -1) {
        // Fallback: pick global minimum approx
        zero_index = int(min_element(approx.begin() + 1, approx.end()) - approx.begin());
    }

    // Stage 2: determine the permutation using the zero index
    vector<int> ans(n + 1, 0);
    for (int i = 1; i <= n; ++i) {
        if (i == zero_index) continue;
        int x = ask(zero_index, i);
        ans[i] = x;
    }
    ans[zero_index] = 0;

    cout << "! ";
    for (int i = 1; i <= n; ++i) {
        cout << ans[i] << (i == n ? '\n' : ' ');
    }
    cout.flush();

    return 0;
}