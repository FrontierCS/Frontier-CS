#include <bits/stdc++.h>
using namespace std;

static const int OPS_LIMIT = 100000;

int n, k;
int m, tbits;
long long opsCount = 0;

bool ask_query(int c) {
    if (opsCount >= OPS_LIMIT) return false; // safeguard
    cout << "? " << c << endl << flush;
    opsCount++;
    string s;
    while (cin >> s) {
        if (!s.empty()) break;
    }
    if (s.empty()) return false;
    return s[0] == 'Y' || s[0] == 'y';
}

void do_reset() {
    if (opsCount >= OPS_LIMIT) return;
    cout << "R" << endl << flush;
    opsCount++;
}

// Multiply m x m binary matrix A by vector v (m-bit int). A is represented as vector<int> rows where rows[r] is bitmask of row r.
int mul_mat_vec(const vector<int>& A, int v, int m) {
    int res = 0;
    for (int r = 0; r < m; ++r) {
        int dot = __builtin_parity(A[r] & v);
        if (dot) res |= (1 << r);
    }
    return res;
}

// Invert m x m binary matrix A. Returns true if invertible and sets inv to inverse.
bool invert_matrix(vector<int> A, vector<int>& inv, int m) {
    inv.assign(m, 0);
    for (int i = 0; i < m; ++i) inv[i] = (1 << i);
    for (int col = 0, row = 0; col < m && row < m; ++col) {
        int sel = -1;
        for (int i = row; i < m; ++i) {
            if ((A[i] >> col) & 1) { sel = i; break; }
        }
        if (sel == -1) continue;
        swap(A[sel], A[row]);
        swap(inv[sel], inv[row]);
        for (int i = 0; i < m; ++i) {
            if (i != row && ((A[i] >> col) & 1)) {
                A[i] ^= A[row];
                inv[i] ^= inv[row];
            }
        }
        row++;
    }
    // Check if A is identity now
    for (int i = 0; i < m; ++i) {
        if (A[i] != (1 << i)) return false;
    }
    return true;
}

// Generate a random invertible m x m matrix over GF(2)
vector<int> random_invertible_matrix(int m, mt19937& rng) {
    uniform_int_distribution<int> dist(0, (1<<m)-1);
    vector<int> A(m);
    while (true) {
        for (int i = 0; i < m; ++i) {
            A[i] = dist(rng);
        }
        vector<int> inv;
        if (invert_matrix(A, inv, m)) {
            return A;
        }
    }
}

// Compose H and L into an m-bit j given the mask T of size tbits
int compose_HL_to_j(int H, int L, int m, int tbits, int Tmask) {
    int j = 0;
    int idxH = 0, idxL = 0;
    for (int pos = 0; pos < m; ++pos) {
        if ((Tmask >> pos) & 1) {
            // take from L
            int bit = (L >> idxL) & 1;
            if (bit) j |= (1 << pos);
            idxL++;
        } else {
            int bit = (H >> idxH) & 1;
            if (bit) j |= (1 << pos);
            idxH++;
        }
    }
    return j;
}

// Generate all subsets of {0..m-1} of size tbits as bitmasks
void gen_subsets_size_t(int m, int tbits, vector<int>& subsets) {
    subsets.clear();
    if (tbits == 0) {
        subsets.push_back(0);
        return;
    }
    vector<int> comb;
    function<void(int,int)> dfs = [&](int start, int left) {
        if (left == 0) {
            int mask = 0;
            for (int x : comb) mask |= (1 << x);
            subsets.push_back(mask);
            return;
        }
        for (int i = start; i <= m - left; ++i) {
            comb.push_back(i);
            dfs(i + 1, left - 1);
            comb.pop_back();
        }
    };
    dfs(0, tbits);
}

// Fisher-Yates shuffle for vector
template<typename T>
void shuffle_vec(vector<T>& v, mt19937& rng) {
    shuffle(v.begin(), v.end(), rng);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n >> k)) {
        return 0;
    }
    // compute m and tbits
    m = 0; { int tmp = n; while ((1 << m) < n) m++; }
    tbits = 0; { int tmp = k; while ((1 << tbits) < k) tbits++; }

    vector<char> active(n, 1);
    int active_cnt = n;

    // Precompute subsets of size tbits
    vector<int> T_subsets;
    gen_subsets_size_t(m, tbits, T_subsets);

    // RNG
    mt19937 rng((unsigned)chrono::high_resolution_clock::now().time_since_epoch().count());
    shuffle_vec(T_subsets, rng);

    // Prepare transforms: identity + some random transforms, but limited by budget
    vector<vector<int>> transforms;
    vector<int> Irows(m);
    for (int i = 0; i < m; ++i) Irows[i] = (1 << i);
    transforms.push_back(Irows);

    // Estimate available partitions we can process within OPS_LIMIT
    auto est_partition_cost = [&](int cur_active)->int{
        int blocks = n / max(1, k);
        return blocks + cur_active; // resets + queries (approx)
    };
    int max_partitions = 0;
    {
        int budget = OPS_LIMIT - 10; // reserve
        int est = est_partition_cost(active_cnt);
        if (est <= 0) est = 1;
        max_partitions = budget / est;
        // cap at something reasonable to avoid long runtime
        max_partitions = max(1, min(max_partitions, 10000));
    }

    // Decide number of transforms based on max partitions and number of subsets per transform
    int subsets_per_transform = (int)T_subsets.size();
    int max_transforms = (subsets_per_transform == 0 ? 0 : max_partitions / max(1, subsets_per_transform));
    max_transforms = max(1, max_transforms); // at least identity
    // cap transforms to avoid excessive work
    max_transforms = min(max_transforms, 16); // heuristic cap to avoid too many random matrices

    // Generate random transforms
    for (int ti = 1; ti < max_transforms; ++ti) {
        transforms.push_back(random_invertible_matrix(m, rng));
    }

    // Run elimination passes
    int partitions_used = 0;
    for (const auto& A : transforms) {
        vector<int> Ainverse;
        if (!invert_matrix(A, Ainverse, m)) continue; // should be invertible
        vector<int> Torder = T_subsets;
        shuffle_vec(Torder, rng);
        for (int Tmask : Torder) {
            if (opsCount >= OPS_LIMIT) break;
            // For each block H (m - tbits bits)
            int Hmax = 1 << max(0, m - tbits);
            vector<int> Horder(Hmax);
            iota(Horder.begin(), Horder.end(), 0);
            shuffle_vec(Horder, rng);
            for (int H : Horder) {
                if (opsCount >= OPS_LIMIT) break;
                // Before resetting ensure at least some active entries exist to avoid wasting operations
                bool hasActive = false;
                // quick check by sampling few Ls
                int sample = 0, limitSample = min(k, 8);
                for (int L = 0; L < k && sample < limitSample; ++L, ++sample) {
                    int j = compose_HL_to_j(H, L, m, tbits, Tmask);
                    int i = mul_mat_vec(Ainverse, j, m);
                    if (i < n && active[i]) { hasActive = true; break; }
                }
                if (!hasActive) continue;

                // reset
                if (opsCount + 1 > OPS_LIMIT) break;
                do_reset();

                // iterate all L in [0, k)
                for (int L = 0; L < k; ++L) {
                    if (opsCount >= OPS_LIMIT) break;
                    int j = compose_HL_to_j(H, L, m, tbits, Tmask);
                    int i = mul_mat_vec(Ainverse, j, m);
                    if (i < 0 || i >= n) continue;
                    if (!active[i]) continue;
                    // ask
                    bool y = ask_query(i + 1);
                    if (y) {
                        active[i] = 0;
                        active_cnt--;
                        if (active_cnt <= 0) break;
                    }
                }
            }
            partitions_used++;
            if (opsCount >= OPS_LIMIT) break;
        }
        if (opsCount >= OPS_LIMIT) break;
    }

    // Final exact verification among remaining active elements using pairwise if budget allows
    vector<int> active_idx;
    for (int i = 0; i < n; ++i) if (active[i]) active_idx.push_back(i);

    int r = (int)active_idx.size();
    // Solve if we can afford pairwise tests: cost ~ 3 * r*(r-1)/2
    long long remaining_ops = OPS_LIMIT - opsCount;
    long long need_ops = 3LL * r * (r - 1) / 2;
    if (need_ops <= remaining_ops && r > 0) {
        // DSU
        vector<int> parent(r);
        iota(parent.begin(), parent.end(), 0);
        function<int(int)> findp = [&](int x){ return parent[x]==x?x:parent[x]=findp(parent[x]); };
        auto unite = [&](int a, int b){
            a = findp(a); b = findp(b);
            if (a != b) parent[b] = a;
        };
        for (int i = 0; i < r; ++i) {
            for (int j = i + 1; j < r; ++j) {
                if (opsCount + 3 > OPS_LIMIT) break;
                do_reset();
                bool y1 = ask_query(active_idx[i] + 1);
                (void)y1; // response ignored
                bool y2 = ask_query(active_idx[j] + 1);
                if (y2) {
                    unite(i, j);
                }
            }
            if (opsCount >= OPS_LIMIT) break;
        }
        // Count components
        vector<int> seen(r, 0);
        int comps = 0;
        for (int i = 0; i < r; ++i) {
            int p = findp(i);
            if (!seen[p]) { seen[p] = 1; comps++; }
        }
        // comps is the final distinct count among active; eliminated ones are duplicates
        // Final d equals comps
        cout << "! " << comps << endl << flush;
        return 0;
    } else {
        // Output current active count as estimate of remaining distinct
        // This is correct if elimination removed all duplicates among active; otherwise might be overestimated.
        cout << "! " << r << endl << flush;
        return 0;
    }
}