#include <bits/stdc++.h>
using namespace std;

struct Interactor {
    int n, k;
    int ops = 0, resets = 0, queries = 0;

    explicit Interactor(int n_, int k_) : n(n_), k(k_) {}

    void do_reset() {
        cout << "R\n";
        cout.flush();
        ++ops;
        ++resets;
    }

    char do_query(int idx) {
        cout << "? " << idx << "\n";
        cout.flush();
        ++ops;
        ++queries;
        char r;
        if (!(cin >> r)) exit(0);
        return r;
    }

    [[noreturn]] void answer(int d) {
        cout << "! " << d << "\n";
        cout.flush();
        exit(0);
    }
};

static int choose_best_g(int a, int b, int k) {
    if (a <= 0) return 0;
    int maxg = min(a, k - 1);
    long long best = (1LL << 62);
    int bestg = 1;

    for (int g = 1; g <= maxg; ++g) {
        int q = k - g;
        int num = (b + q - 1) / q;
        long long cost_group = 1LL + b + 1LL * num * g;
        long long groups = (a + g - 1) / g;
        long long total = cost_group * groups;
        if (total < best) {
            best = total;
            bestg = g;
        }
    }
    return bestg;
}

static void merge_into(Interactor &it, vector<int> &global_reps, vector<int> block_reps) {
    if (block_reps.empty()) return;
    if (global_reps.empty()) {
        global_reps = std::move(block_reps);
        return;
    }

    vector<int> B = std::move(block_reps);

    int g_step = choose_best_g((int)global_reps.size(), (int)B.size(), it.k);
    if (g_step <= 0) {
        for (int x : B) global_reps.push_back(x);
        return;
    }

    for (int start = 0; start < (int)global_reps.size() && !B.empty(); start += g_step) {
        int g = min(g_step, (int)global_reps.size() - start);
        int q = it.k - g;

        it.do_reset();
        for (int i = 0; i < g; ++i) (void)it.do_query(global_reps[start + i]);

        int pos = 0;
        while (pos < (int)B.size()) {
            int take = min(q, (int)B.size() - pos);
            for (int j = 0; j < take; ++j) {
                char r = it.do_query(B[pos + j]);
                if (r == 'Y') B[pos + j] = -1;
            }
            pos += take;
            if (pos < (int)B.size()) {
                for (int i = 0; i < g; ++i) (void)it.do_query(global_reps[start + i]);
            }
        }

        vector<int> Bnew;
        Bnew.reserve(B.size());
        for (int x : B) if (x != -1) Bnew.push_back(x);
        B.swap(Bnew);
    }

    for (int x : B) global_reps.push_back(x);
}

static vector<int> get_block_reps(Interactor &it, int L, int R) {
    vector<int> reps;
    reps.reserve(R - L + 1);
    it.do_reset();
    for (int idx = L; idx <= R; ++idx) {
        char r = it.do_query(idx);
        if (r == 'N') reps.push_back(idx);
    }
    return reps;
}

static int solve_k1(Interactor &it) {
    vector<int> reps;
    reps.reserve(it.n);

    for (int i = 1; i <= it.n; ++i) {
        bool found = false;
        if (!reps.empty()) {
            it.do_reset();
            (void)it.do_query(i); // load i into memory
            for (int r : reps) {
                char ans = it.do_query(r); // compares r with i
                if (ans == 'Y') {
                    found = true;
                    break;
                }
                (void)it.do_query(i); // restore i in memory for next comparison
            }
        }
        if (!found) reps.push_back(i);
    }
    return (int)reps.size();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, k;
    cin >> n >> k;

    Interactor it(n, k);

    if (k >= n) {
        it.do_reset();
        int d = 0;
        for (int i = 1; i <= n; ++i) {
            if (it.do_query(i) == 'N') ++d;
        }
        it.answer(d);
    }

    if (k == 1) {
        int d = solve_k1(it);
        it.answer(d);
    }

    int block = k;               // n and k are powers of 2, so n % k == 0
    int blocks = n / block;

    vector<int> global_reps;
    global_reps.reserve(n);

    for (int b = 0; b < blocks; ++b) {
        int L = b * block + 1;
        int R = (b + 1) * block;
        vector<int> reps = get_block_reps(it, L, R);
        merge_into(it, global_reps, std::move(reps));
    }

    it.answer((int)global_reps.size());
    return 0;
}