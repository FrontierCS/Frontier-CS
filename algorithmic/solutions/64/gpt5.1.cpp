#include <bits/stdc++.h>
using namespace std;

struct Node {
    long long sum;
    uint32_t mask;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long T;
    if (!(cin >> n >> T)) return 0;
    vector<long long> a(n);
    for (int i = 0; i < n; ++i) cin >> a[i];

    vector<int> best_bits(n, 0);
    long long best_sum = 0;
    long long best_err = llabs(T - 0);

    if (n <= 40) {
        int n1 = n / 2;
        int n2 = n - n1;
        vector<long long> a1(n1), a2(n2);
        for (int i = 0; i < n1; ++i) a1[i] = a[i];
        for (int i = 0; i < n2; ++i) a2[i] = a[n1 + i];
        int size1 = 1 << n1;
        int size2 = 1 << n2;
        vector<Node> left(size1), right(size2);
        left[0].sum = 0;
        left[0].mask = 0;
        for (int mask = 1; mask < size1; ++mask) {
            int b = __builtin_ctz(mask);
            int prev = mask & (mask - 1);
            left[mask].sum = left[prev].sum + a1[b];
            left[mask].mask = mask;
        }
        right[0].sum = 0;
        right[0].mask = 0;
        for (int mask = 1; mask < size2; ++mask) {
            int b = __builtin_ctz(mask);
            int prev = mask & (mask - 1);
            right[mask].sum = right[prev].sum + a2[b];
            right[mask].mask = mask;
        }
        sort(right.begin(), right.end(), [](const Node &x, const Node &y) {
            return x.sum < y.sum;
        });
        best_err = llabs(T);
        best_sum = 0;
        for (int i = 0; i < size1; ++i) {
            long long s1 = left[i].sum;
            long long need = T - s1;
            auto it = lower_bound(
                right.begin(), right.end(), need,
                [](const Node &nd, const long long val) { return nd.sum < val; });
            if (it != right.end()) {
                long long cand_sum = s1 + it->sum;
                long long err = llabs(cand_sum - T);
                if (err < best_err) {
                    best_err = err;
                    best_sum = cand_sum;
                    uint32_t lm = left[i].mask;
                    uint32_t rm = it->mask;
                    for (int k = 0; k < n1; ++k) best_bits[k] = ((lm >> k) & 1);
                    for (int k = 0; k < n2; ++k) best_bits[n1 + k] = ((rm >> k) & 1);
                }
            }
            if (it != right.begin()) {
                --it;
                long long cand_sum = s1 + it->sum;
                long long err = llabs(cand_sum - T);
                if (err < best_err) {
                    best_err = err;
                    best_sum = cand_sum;
                    uint32_t lm = left[i].mask;
                    uint32_t rm = it->mask;
                    for (int k = 0; k < n1; ++k) best_bits[k] = ((lm >> k) & 1);
                    for (int k = 0; k < n2; ++k) best_bits[n1 + k] = ((rm >> k) & 1);
                }
            }
            if (best_err == 0) break;
        }
        for (int i = 0; i < n; ++i) cout << (best_bits[i] ? '1' : '0');
        cout << '\n';
        return 0;
    }

    // Heuristic for n > 40
    mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());

    auto eval_update_global = [&](const vector<int> &bits, long long sum) {
        long long err = llabs(sum - T);
        if (err < best_err) {
            best_err = err;
            best_sum = sum;
            best_bits = bits;
        }
    };

    vector<int> idx(n);
    iota(idx.begin(), idx.end(), 0);
    vector<int> desc = idx, asc = idx;
    sort(desc.begin(), desc.end(), [&](int i, int j) { return a[i] > a[j]; });
    sort(asc.begin(), asc.end(), [&](int i, int j) { return a[i] < a[j]; });

    // Partial meet-in-the-middle on up to 40 largest elements
    {
        int m = min(40, n);
        vector<int> top(m);
        for (int i = 0; i < m; ++i) top[i] = desc[i];
        int m1 = m / 2;
        int m2 = m - m1;
        vector<long long> b1(m1), b2(m2);
        for (int i = 0; i < m1; ++i) b1[i] = a[top[i]];
        for (int i = 0; i < m2; ++i) b2[i] = a[top[m1 + i]];
        int size1 = 1 << m1;
        int size2 = 1 << m2;
        vector<Node> left(size1), right(size2);
        left[0].sum = 0;
        left[0].mask = 0;
        for (int mask = 1; mask < size1; ++mask) {
            int b = __builtin_ctz(mask);
            int prev = mask & (mask - 1);
            left[mask].sum = left[prev].sum + b1[b];
            left[mask].mask = mask;
        }
        right[0].sum = 0;
        right[0].mask = 0;
        for (int mask = 1; mask < size2; ++mask) {
            int b = __builtin_ctz(mask);
            int prev = mask & (mask - 1);
            right[mask].sum = right[prev].sum + b2[b];
            right[mask].mask = mask;
        }
        sort(right.begin(), right.end(), [](const Node &x, const Node &y) {
            return x.sum < y.sum;
        });
        long long local_best_err = llabs(T);
        uint32_t best_lm = 0, best_rm = 0;
        for (int i = 0; i < size1; ++i) {
            long long s_left = left[i].sum;
            long long need = T - s_left;
            auto it = lower_bound(
                right.begin(), right.end(), need,
                [](const Node &nd, const long long val) { return nd.sum < val; });
            if (it != right.end()) {
                long long cand_sum = s_left + it->sum;
                long long err = llabs(cand_sum - T);
                if (err < local_best_err) {
                    local_best_err = err;
                    best_lm = left[i].mask;
                    best_rm = it->mask;
                }
            }
            if (it != right.begin()) {
                --it;
                long long cand_sum = s_left + it->sum;
                long long err = llabs(cand_sum - T);
                if (err < local_best_err) {
                    local_best_err = err;
                    best_lm = left[i].mask;
                    best_rm = it->mask;
                }
            }
            if (local_best_err == 0) break;
        }
        vector<int> bits0(n, 0);
        long long sum0 = 0;
        for (int k = 0; k < m1; ++k) {
            if ((best_lm >> k) & 1u) {
                bits0[top[k]] = 1;
                sum0 += a[top[k]];
            }
        }
        for (int k = 0; k < m2; ++k) {
            if ((best_rm >> k) & 1u) {
                bits0[top[m1 + k]] = 1;
                sum0 += a[top[m1 + k]];
            }
        }
        eval_update_global(bits0, sum0);
    }

    auto greedy_with_order = [&](const vector<int> &order) {
        vector<int> bits(n, 0);
        long long sum = 0;
        for (int idx0 : order) {
            long long add = a[idx0];
            long long new_sum = sum + add;
            if (llabs(new_sum - T) <= llabs(sum - T)) {
                bits[idx0] = 1;
                sum = new_sum;
            }
        }
        eval_update_global(bits, sum);
        return make_pair(bits, sum);
    };

    const int RESTARTS = 25;
    const int MAX_PASSES = 25;

    for (int iter = 0; iter < RESTARTS && best_err > 0; ++iter) {
        vector<int> bits(n, 0);
        long long sum = 0;
        if (iter == 0) {
            auto res = greedy_with_order(desc);
            bits = res.first;
            sum = res.second;
        } else if (iter == 1) {
            auto res = greedy_with_order(asc);
            bits = res.first;
            sum = res.second;
        } else if (iter == 2) {
            sum = 0;
            for (int i = 0; i < n; ++i) {
                bits[i] = (rng() & 1);
                if (bits[i]) sum += a[i];
            }
            eval_update_global(bits, sum);
        } else {
            vector<int> ord = idx;
            shuffle(ord.begin(), ord.end(), rng);
            auto res = greedy_with_order(ord);
            bits = res.first;
            sum = res.second;
        }
        long long err = llabs(sum - T);
        if (err == 0) {
            best_err = 0;
            best_sum = sum;
            best_bits = bits;
            break;
        }

        for (int pass = 0; pass < MAX_PASSES && err > 0; ++pass) {
            bool improved = false;
            // 1-opt
            vector<int> ord = idx;
            shuffle(ord.begin(), ord.end(), rng);
            for (int id : ord) {
                long long delta = bits[id] ? -a[id] : +a[id];
                long long new_sum = sum + delta;
                long long new_err = llabs(new_sum - T);
                if (new_err < err) {
                    bits[id] ^= 1;
                    sum = new_sum;
                    err = new_err;
                    improved = true;
                    if (err < best_err) {
                        best_err = err;
                        best_sum = sum;
                        best_bits = bits;
                    }
                    if (err == 0) break;
                }
            }
            if (err == 0) break;
            // 2-opt
            bool improved2 = false;
            for (int i = 0; i < n && !improved2; ++i) {
                long long di = bits[i] ? -a[i] : +a[i];
                for (int j = i + 1; j < n; ++j) {
                    long long dj = bits[j] ? -a[j] : +a[j];
                    long long new_sum = sum + di + dj;
                    long long new_err = llabs(new_sum - T);
                    if (new_err < err) {
                        bits[i] ^= 1;
                        bits[j] ^= 1;
                        sum = new_sum;
                        err = new_err;
                        improved2 = true;
                        improved = true;
                        if (err < best_err) {
                            best_err = err;
                            best_sum = sum;
                            best_bits = bits;
                        }
                        break;
                    }
                }
            }
            if (err == 0) break;
            if (!improved) break;
        }
    }

    for (int i = 0; i < n; ++i) cout << (best_bits[i] ? '1' : '0');
    cout << '\n';
    return 0;
}