#include <bits/stdc++.h>
using namespace std;

const int MAXN = 505;
const int MAXT = 1005; // 2*n-1 <= 999 for n<=500

int G[MAXN][MAXN];
int L_T[MAXT]; // L_T[T] = min value on anti-diagonal i+j = T+1
int n, m;
bool queried[MAXN][MAXT]; // queried[l][T]
vector<int> all_values;

// prefix max for row 1
int pref_max[MAXN];

void read_grid() {
    cin >> n >> m;
    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j++) {
            cin >> G[i][j];
        }
    }
    // precompute prefix max of row 1
    pref_max[0] = 0;
    for (int i = 1; i <= n; i++) {
        pref_max[i] = max(pref_max[i-1], G[1][i]);
    }
}

void precompute_L_T() {
    int maxT = 2*n-1;
    for (int T = 1; T <= maxT; T++) {
        int s = T+1; // i+j = s
        L_T[T] = INT_MAX;
        for (int i = 1; i <= n; i++) {
            int j = s - i;
            if (j >= 1 && j <= n) {
                L_T[T] = min(L_T[T], G[i][j]);
            }
        }
    }
}

int ask(int l, int T) {
    cout << "? " << l << " " << T << endl;
    cout.flush();
    int res;
    cin >> res;
    return res;
}

void solve_testcase() {
    read_grid();
    precompute_L_T();
    int maxT = 2*n-1;

    // Initialize queried matrix
    for (int l = 1; l <= n; l++) {
        for (int T = 1; T <= maxT; T++) {
            queried[l][T] = false;
        }
    }

    all_values.clear();

    // Add f(l,1) and f(l,2) for all l
    for (int l = 1; l <= n; l++) {
        // T=1
        int f1 = pref_max[l];
        all_values.push_back(f1);
        queried[l][1] = true;
        // T=2
        int tail_max = (l-1 >= 1) ? pref_max[l-1] : 0;
        int f2 = max(G[2][1], tail_max);
        all_values.push_back(f2);
        queried[l][2] = true;
    }

    // Determine L0: we will query all T for l >= L0
    int big_l_count = (120 * n) / (2*n-3);
    int L0 = n - big_l_count + 1;
    if (L0 < 1) L0 = 1;

    // Query all T for big l
    for (int l = L0; l <= n; l++) {
        for (int T = 3; T <= maxT; T++) {
            int val = ask(l, T);
            all_values.push_back(val);
            queried[l][T] = true;
        }
    }

    // For small l (1..L0-1), we will query some T based on L_T
    int small_l_count = L0 - 1;
    if (small_l_count > 0) {
        // Create list of T (3..maxT) sorted by L_T ascending
        vector<int> sorted_T;
        for (int T = 3; T <= maxT; T++) {
            sorted_T.push_back(T);
        }
        sort(sorted_T.begin(), sorted_T.end(), [](int a, int b) {
            return L_T[a] < L_T[b];
        });

        // How many queries we have used so far for big l?
        int used_queries = (n - L0 + 1) * (maxT - 2); // T=3..maxT
        int remaining_init = 120 * n - used_queries;
        int K = remaining_init / small_l_count;
        if (K < 0) K = 0;
        if (K > (int)sorted_T.size()) K = sorted_T.size();

        for (int l = 1; l <= L0-1; l++) {
            for (int i = 0; i < K; i++) {
                int T = sorted_T[i];
                if (!queried[l][T]) {
                    int val = ask(l, T);
                    all_values.push_back(val);
                    queried[l][T] = true;
                }
            }
        }
    }

    // Now we have a collection of values. We'll iteratively verify and query more if needed.
    int total_queries_so_far = (n - L0 + 1) * (maxT - 2) + (L0-1) * min(K, (int)sorted_T.size());
    int remaining_total = (120 * n + m) - total_queries_so_far;
    // We'll run a few rounds of verification
    const int MAX_ITER = 10;
    for (int iter = 0; iter < MAX_ITER && remaining_total > 0; iter++) {
        sort(all_values.begin(), all_values.end());
        int V = (m-1 < (int)all_values.size()) ? all_values[m-1] : INT_MAX;
        // Collect unqueried pairs (l,T) with L_T[T] <= V
        vector<pair<int,int>> to_query;
        for (int T = 1; T <= maxT; T++) {
            if (L_T[T] > V) continue;
            for (int l = 1; l <= L0-1; l++) {
                if (!queried[l][T]) {
                    to_query.push_back({l, T});
                }
            }
        }
        if (to_query.empty()) break;
        if ((int)to_query.size() <= remaining_total) {
            // query all
            for (auto &p : to_query) {
                int l = p.first, T = p.second;
                int val = ask(l, T);
                all_values.push_back(val);
                queried[l][T] = true;
            }
            remaining_total -= to_query.size();
        } else {
            // too many, query those with smallest L_T first
            sort(to_query.begin(), to_query.end(), [](const pair<int,int> &a, const pair<int,int> &b) {
                return L_T[a.second] < L_T[b.second];
            });
            int can_query = min((int)to_query.size(), remaining_total);
            for (int i = 0; i < can_query; i++) {
                int l = to_query[i].first, T = to_query[i].second;
                int val = ask(l, T);
                all_values.push_back(val);
                queried[l][T] = true;
            }
            remaining_total -= can_query;
            break; // no more queries
        }
    }

    // Finally, output the answer
    sort(all_values.begin(), all_values.end());
    cout << "!";
    for (int i = 0; i < m; i++) {
        cout << " " << all_values[i];
    }
    cout << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    cin >> t;
    while (t--) {
        solve_testcase();
    }
    return 0;
}