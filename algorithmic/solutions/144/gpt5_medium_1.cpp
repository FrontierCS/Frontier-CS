#include <bits/stdc++.h>
using namespace std;

int n;
mt19937 rng((uint32_t)chrono::steady_clock::now().time_since_epoch().count());

pair<int,int> query(const vector<int>& idxs) {
    cout << 0 << ' ' << idxs.size();
    for (int x : idxs) cout << ' ' << x;
    cout << '\n';
    cout.flush();
    int a, b;
    if (!(cin >> a >> b)) {
        // If interaction fails, exit
        exit(0);
    }
    return {a, b};
}

int get_random_excluding(int limit, const vector<int>& exclude_flags) {
    // limit is n, exclude_flags[1..n] indicates excluded (1) or included (0)
    // Return a random index in [1..n] where exclude_flags[idx]==0
    while (true) {
        int x = (int)(rng() % limit) + 1;
        if (!exclude_flags[x]) return x;
    }
}

void pick_random_triple(const vector<int>& pool, int& a, int& b, int& c) {
    int sz = pool.size();
    uniform_int_distribution<int> dist(0, sz - 1);
    int ia = dist(rng);
    int ib = dist(rng);
    while (ib == ia) ib = dist(rng);
    int ic = dist(rng);
    while (ic == ia || ic == ib) ic = dist(rng);
    a = pool[ia];
    b = pool[ib];
    c = pool[ic];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    // Initial full query to get global medians
    vector<int> all(n);
    iota(all.begin(), all.end(), 1);
    auto full = query(all);
    int med1 = min(full.first, full.second);
    int med2 = max(full.first, full.second);

    // Initial passes to gather candidates
    int initial_passes = 3; // number of passes over all indices
    vector<int> hits1(n+1, 0), hits2(n+1, 0);

    auto run_pass = [&](void){
        for (int i = 1; i <= n; ++i) {
            // pool is all except i
            vector<int> pool;
            pool.reserve(n-1);
            for (int j = 1; j <= n; ++j) if (j != i) pool.push_back(j);
            int a, b, c;
            pick_random_triple(pool, a, b, c);
            vector<int> q = {i, a, b, c};
            auto res = query(q);
            if (res.first == med1 || res.second == med1) hits1[i]++;
            if (res.first == med2 || res.second == med2) hits2[i]++;
        }
    };

    for (int p = 0; p < initial_passes; ++p) run_pass();

    auto build_candidates = [&](int target, const vector<int>& hits) {
        vector<int> cand;
        for (int i = 1; i <= n; ++i) if (hits[i] > 0) cand.push_back(i);
        return cand;
    };

    vector<int> C1 = build_candidates(med1, hits1);
    vector<int> C2 = build_candidates(med2, hits2);

    // Ensure both candidate sets are non-empty; add extra passes if necessary up to a limit
    int extra_pass_limit = 2;
    int extra_done = 0;
    while ((C1.empty() || C2.empty()) && extra_done < extra_pass_limit) {
        run_pass();
        C1 = build_candidates(med1, hits1);
        C2 = build_candidates(med2, hits2);
        extra_done++;
    }
    // Build pools excluding candidate sets for refinement
    auto build_pool_excluding_set = [&](const vector<int>& candSet) {
        vector<char> isCand(n+1, 0);
        for (int x : candSet) if (x >= 1 && x <= n) isCand[x] = 1;
        vector<int> pool;
        pool.reserve(n);
        for (int i = 1; i <= n; ++i) if (!isCand[i]) pool.push_back(i);
        return pool;
    };

    auto refine = [&](const vector<int>& candidates, int target) -> int {
        // pool excludes all candidates
        vector<int> pool = build_pool_excluding_set(candidates);
        // If pool too small (unlikely), fall back to excluding none
        if ((int)pool.size() < 3) {
            pool.clear();
            for (int i = 1; i <= n; ++i) pool.push_back(i);
        }

        const int max_attempts_per_candidate = 7;

        // Try each candidate: only the true one can yield 'target' when companions are from pool (since pool excludes all candidates)
        for (int cand : candidates) {
            // Ensure cand is not in pool; if it is (due to fallback), we need to avoid selecting it in triplets
            vector<int> effective_pool;
            effective_pool.reserve(pool.size());
            for (int x : pool) if (x != cand) effective_pool.push_back(x);
            if ((int)effective_pool.size() < 3) {
                // fallback: rebuild from all excluding cand
                effective_pool.clear();
                for (int i = 1; i <= n; ++i) if (i != cand) effective_pool.push_back(i);
            }
            for (int attempt = 0; attempt < max_attempts_per_candidate; ++attempt) {
                int a, b, c;
                pick_random_triple(effective_pool, a, b, c);
                vector<int> q = {cand, a, b, c};
                auto res = query(q);
                if (res.first == target || res.second == target) {
                    return cand;
                }
            }
        }
        // If not found (very unlikely), as a fallback try random indices until found
        // But to keep query count reasonable, try a few random picks from candidates again
        for (int tries = 0; tries < (int)candidates.size() * 3 + 10; ++tries) {
            int cand = candidates[rng() % candidates.size()];
            vector<int> effective_pool;
            effective_pool.reserve(n-1);
            for (int i = 1; i <= n; ++i) if (i != cand) effective_pool.push_back(i);
            int a, b, c;
            pick_random_triple(effective_pool, a, b, c);
            vector<int> q = {cand, a, b, c};
            auto res = query(q);
            if (res.first == target || res.second == target) {
                return cand;
            }
        }
        // As last resort, return any candidate (should not happen)
        return candidates.empty() ? 1 : candidates[0];
    };

    // If candidate sets still empty (extremely unlikely), fall back to brute random search
    if (C1.empty()) {
        // Fill with all indices to avoid crash; refine will try to detect
        for (int i = 1; i <= n; ++i) C1.push_back(i);
    }
    int idx1 = refine(C1, med1);

    if (C2.empty()) {
        for (int i = 1; i <= n; ++i) C2.push_back(i);
    }
    // Remove idx1 from C2 if present to avoid ambiguity (not strictly necessary)
    {
        vector<int> newC2;
        for (int x : C2) if (x != idx1) newC2.push_back(x);
        if (!newC2.empty()) C2.swap(newC2);
    }
    int idx2 = refine(C2, med2);

    cout << 1 << ' ' << idx1 << ' ' << idx2 << '\n';
    cout.flush();
    return 0;
}