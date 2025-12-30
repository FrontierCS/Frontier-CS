#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

const long long INF = 1e18;

struct Node {
    Node *l = nullptr, *r = nullptr;
    long long max_val = 0;
};

void update(Node*& curr, int tl, int tr, int pos, long long val) {
    if (!curr) {
        curr = new Node();
    }
    curr->max_val = max(curr->max_val, val);
    if (tl == tr) {
        return;
    }
    int tm = tl + (tr - tl) / 2;
    if (pos <= tm) {
        update(curr->l, tl, tm, pos, val);
    } else {
        update(curr->r, tm + 1, tr, pos, val);
    }
}

long long query(Node* curr, int tl, int tr, int l, int r) {
    if (!curr || l > r) {
        return 0;
    }
    if (l == tl && r == tr) {
        return curr->max_val;
    }
    int tm = tl + (tr - tl) / 2;
    return max(query(curr->l, tl, tm, l, min(r, tm)),
               query(curr->r, tm + 1, tr, max(l, tm + 1), r));
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;
    vector<int> v(n);
    vector<int> pos(n + 1);
    for (int i = 0; i < n; ++i) {
        cin >> v[i];
        pos[v[i]] = i;
    }

    vector<map<int, long long>> dp_val(n + 1);
    
    vector<Node*> fts(n + 2, nullptr);

    for (int i = 0; i < n; ++i) {
        int val = v[i];
        
        update(fts[1], 1, n, val, val);
        dp_val[val][1] = val;
        
        for (int k = i + 1; k >= 2; --k) {
            long long prev_max_sum = query(fts[k - 1], 1, n, 1, val - 1);
            if (prev_max_sum > 0) {
                long long current_sum = val + prev_max_sum;
                if (!dp_val[val].count(k) || current_sum > dp_val[val][k]) {
                    update(fts[k], 1, n, val, current_sum);
                    dp_val[val][k] = current_sum;
                }
            }
        }
    }

    vector<long long> max_sum_k(n + 1, 0);
    for (int val = 1; val <= n; ++val) {
        for(auto const& [k, sum] : dp_val[val]) {
            if (k <= n)
                max_sum_k[k] = max(max_sum_k[k], sum);
        }
    }

    long long best_final_cost = -1;
    int best_k = -1;

    long long sum_all = (long long)n * (n + 1) / 2;

    for (int k = 0; k <= n; ++k) {
        if (k > 0 && max_sum_k[k] == 0) continue;
        
        long long s = (k == 0) ? 0 : max_sum_k[k];
        long long num_moves = n - k;
        
        long long current_total_cost;
        if (k > 0) {
            current_total_cost = num_moves + (long long)n * k - s - (long long)k * (k - 1) / 2;
        } else {
            current_total_cost = sum_all;
        }

        long long final_cost = (current_total_cost + 1) * (num_moves + 1);
        if (k==n) final_cost = 1;

        if (best_k == -1 || final_cost < best_final_cost) {
            best_final_cost = final_cost;
            best_k = k;
        }
    }
    
    if (n==0) {
        cout << "1 0" << endl;
        return 0;
    }
    if (best_k == -1) best_k = n;
    
    vector<int> s_elements;
    vector<bool> is_in_s(n + 1, false);

    if (best_k > 0) {
        long long target_sum = max_sum_k[best_k];
        int last_val = -1;
        for (int val = n; val >= 1; --val) {
            if (dp_val[val].count(best_k) && dp_val[val][best_k] == target_sum) {
                last_val = val;
                break;
            }
        }
        
        for (int k = best_k; k >= 1; --k) {
            s_elements.push_back(last_val);
            target_sum -= last_val;
            if (k > 1) {
                int next_last_val = -1;
                for (int p_val = last_val - 1; p_val >= 1; --p_val) {
                     if (pos[p_val] < pos[last_val] && dp_val[p_val].count(k-1) && dp_val[p_val][k-1] == target_sum) {
                        next_last_val = p_val;
                        break;
                    }
                }
                last_val = next_last_val;
            }
        }
        reverse(s_elements.begin(), s_elements.end());
    }

    for (int val : s_elements) {
        is_in_s[val] = true;
    }

    vector<int> m_elements;
    for (int i = 1; i <= n; ++i) {
        if (!is_in_s[i]) {
            m_elements.push_back(i);
        }
    }
    sort(m_elements.rbegin(), m_elements.rend());
    
    if (best_k == n) best_final_cost = 1;
    cout << best_final_cost << " " << m_elements.size() << endl;

    vector<int> current_v = v;

    for (int val_to_move : m_elements) {
        int y = 1;
        for (int s_val : s_elements) {
            if (s_val < val_to_move) {
                y++;
            }
        }
        int x = -1;
        for(int i=0; i < (int)current_v.size(); ++i) {
            if (current_v[i] == val_to_move) {
                x = i + 1;
                break;
            }
        }
        cout << x << " " << y << endl;
        
        current_v.erase(current_v.begin() + x - 1);
        current_v.insert(current_v.begin() + y - 1, val_to_move);
    }

    return 0;
}