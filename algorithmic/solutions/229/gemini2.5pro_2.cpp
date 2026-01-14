#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <functional>

using namespace std;

const long long INF = 2e18;

int n;
long long x;
vector<int> t;

template <typename T>
struct RMQ {
    vector<vector<T>> st;
    vector<int> log_table;
    using Comp = function<T(T, T)>;
    Comp comp;

    RMQ(const vector<int>& a, Comp c) : comp(c) {
        int len = a.size();
        log_table.resize(len + 1);
        log_table[1] = 0;
        for (int i = 2; i <= len; i++) {
            log_table[i] = log_table[i / 2] + 1;
        }

        st.resize(log_table[len] + 1, vector<T>(len));
        for (int i = 0; i < len; i++) {
            st[0][i] = a[i];
        }

        for (int k = 1; k <= log_table[len]; k++) {
            for (int i = 0; i + (1 << k) <= len; i++) {
                st[k][i] = comp(st[k - 1][i], st[k - 1][i + (1 << (k - 1))]);
            }
        }
    }

    T query(int l, int r) { // inclusive
        if (l > r) {
            if (comp(1, -1) > 0) return -2e9; // max
            return 2e9; // min
        }
        int k = log_table[r - l + 1];
        return comp(st[k][l], st[k][r - (1 << k) + 1]);
    }
};

RMQ<int>* rmq_min;
RMQ<int>* rmq_max;

int get_min(int l, int r) {
    if (l > r) return 2e9;
    return rmq_min->query(l, r);
}

int get_max(int l, int r) {
    if (l > r) return 0;
    return rmq_max->query(l, r);
}

int calculate_lis(int l, int r) {
    if (l > r) {
        return 0;
    }
    
    vector<int> tails;
    if (l <= r) {
        tails.push_back(t[l]);
    }

    for (int i = l + 1; i <= r; ++i) {
        if (t[i] > tails.back()) {
            tails.push_back(t[i]);
        } else {
            *lower_bound(tails.begin(), tails.end(), t[i]) = t[i];
        }
    }
    return tails.size();
}

struct Partition {
    vector<int> p;
    long long score;
    long long cost;
    vector<long long> d;

    Partition() : score(0), cost(0) {
        p.resize(12);
    }
};

void evaluate(Partition& part) {
    part.p[0] = 0;
    part.p[11] = n;
    
    vector<pair<int, int>> segments(11);
    for (int i = 0; i < 11; ++i) {
        segments[i] = {part.p[i] + 1, part.p[i+1]};
    }

    long long current_cost = 0;
    for (int i = 0; i < 10; ++i) {
        long long max_i = get_max(segments[i].first - 1, segments[i].second - 1);
        long long min_i1 = get_min(segments[i+1].first - 1, segments[i+1].second - 1);
        if (max_i == 0 || min_i1 > 1e9+7) continue;
        current_cost += max(0LL, max_i - min_i1 + 1);
    }

    part.cost = current_cost;
    if (part.cost > 2 * x) {
        part.score = -1;
        return;
    }
    
    long long total_lis = 0;
    for (int i = 0; i < 11; ++i) {
        total_lis += calculate_lis(segments[i].first - 1, segments[i].second - 1);
    }
    part.score = total_lis;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n >> x;
    t.resize(n);
    for (int i = 0; i < n; i++) {
        cin >> t[i];
    }

    rmq_min = new RMQ<int>(t, [](int a, int b) { return min(a, b); });
    rmq_max = new RMQ<int>(t, [](int a, int b) { return max(a, b); });

    Partition best_part;
    for (int i = 1; i <= 10; ++i) {
        best_part.p[i] = (int)((long long)i * n / 11);
    }
    evaluate(best_part);

    int iterations = 40; 
    if (n > 50000) iterations = 20;
    if (n > 100000) iterations = 10;
    if (n > 150000) iterations = 5;


    for (int iter = 0; iter < iterations; ++iter) {
        bool changed = false;
        Partition current_part = best_part;
        
        Partition best_neighbor_part = best_part;

        for (int k = 1; k <= 10; ++k) {
            for (int dir : {-1, 1}) {
                Partition next_part = current_part;
                int new_pos = next_part.p[k] + dir;
                
                if (new_pos > next_part.p[k-1] && new_pos < next_part.p[k+1]) {
                    next_part.p[k] = new_pos;
                    evaluate(next_part);
                    if (next_part.score > best_neighbor_part.score) {
                        best_neighbor_part = next_part;
                        changed = true;
                    }
                }
            }
        }

        if (changed) {
            best_part = best_neighbor_part;
        } else {
            break;
        }
    }


    cout << best_part.score << "\n";
    
    best_part.d.assign(12, 0);
    vector<pair<int,int>> segments(11);
     for (int i = 0; i < 11; ++i) {
        segments[i] = {best_part.p[i] + 1, best_part.p[i+1]};
    }
    
    for(int i = 0; i < 10; ++i) {
        long long max_i = get_max(segments[i].first - 1, segments[i].second - 1);
        long long min_i1 = get_min(segments[i+1].first - 1, segments[i+1].second - 1);
        long long cost_val = 0;
        if(max_i != 0 && min_i1 < 2e9) {
            cost_val = max(0LL, max_i - min_i1 + 1);
        }
        best_part.d[i+1] = best_part.d[i] + cost_val;
    }

    vector<long long> sorted_d = best_part.d;
    sort(sorted_d.begin(), sorted_d.end());
    long long median_d = sorted_d[5];

    int zero_op_idx = -1;
    for(int i = 0; i < 11; ++i) {
        if (best_part.d[i] == median_d) {
            zero_op_idx = i;
            break;
        }
    }
    if (zero_op_idx == -1) zero_op_idx = 5;

    int op_count = 0;
    for (int i = 0; i < 11 && op_count < 10; ++i) {
        if (i == zero_op_idx) continue;
        if (segments[i].first > segments[i].second) { // Empty segment
            cout << 1 << " " << 1 << " " << 0 << "\n";
        } else {
            cout << segments[i].first << " " << segments[i].second << " " << best_part.d[i] - median_d << "\n";
        }
        op_count++;
    }
    
    while(op_count < 10) {
        cout << 1 << " " << 1 << " " << 0 << "\n";
        op_count++;
    }

    delete rmq_min;
    delete rmq_max;

    return 0;
}