#include <iostream>
#include <vector>
#include <algorithm>
#include <map>

#include <ext/pb_ds/assoc_container.hpp>
#include <ext/pb_ds/tree_policy.hpp>

using namespace __gnu_pbds;

template <typename T>
using ordered_set = tree<T, null_type, std::less<T>, rb_tree_tag, tree_order_statistics_node_update>;

struct Node {
    long long len = 0, sum = 0;
    int val = 0;

    Node operator+(const Node& other) const {
        if (len > other.len) return *this;
        if (other.len > len) return other;
        if (sum > other.sum) return *this;
        if (other.sum > sum) return other;
        if (val > other.val) return *this;
        return other;
    }
};

std::vector<Node> ft;
int ft_size;

void update(int idx, Node node) {
    for (; idx <= ft_size; idx += idx & -idx) {
        ft[idx] = ft[idx] + node;
    }
}

Node query(int idx) {
    Node res;
    for (; idx > 0; idx -= idx & -idx) {
        res = res + ft[idx];
    }
    return res;
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;
    std::vector<int> v(n);
    for (int i = 0; i < n; ++i) {
        std::cin >> v[i];
    }

    ft_size = n;
    ft.assign(n + 1, Node());
    std::vector<int> parent(n + 1, 0);

    for (int i = 0; i < n; ++i) {
        int val = v[i];
        Node best_prev = query(val - 1);
        parent[val] = best_prev.val;
        Node current_node = {best_prev.len + 1, best_prev.sum + val, val};
        update(val, current_node);
    }

    Node best_lis_node = query(n);
    std::vector<int> s;
    int curr = best_lis_node.val;
    while (curr != 0) {
        s.push_back(curr);
        curr = parent[curr];
    }
    std::reverse(s.begin(), s.end());

    std::vector<bool> is_in_s(n + 1, false);
    for (int val : s) {
        is_in_s[val] = true;
    }

    std::vector<int> m;
    for (int i = 1; i <= n; ++i) {
        if (!is_in_s[i]) {
            m.push_back(i);
        }
    }

    long long total_cost = 0;
    std::sort(s.begin(), s.end());
    for (int val : m) {
        long long y = 1 + (std::lower_bound(s.begin(), s.end(), val) - s.begin());
        total_cost += y;
    }

    long long num_moves = m.size();
    long long final_cost = (total_cost + 1) * (num_moves + 1);

    std::cout << final_cost << " " << num_moves << std::endl;

    if (num_moves > 0) {
        using p_type = std::pair<long long, int>;
        ordered_set<p_type> p;
        std::map<int, long long> val_to_time;
        const long long C = 1LL << 40;

        for (int i = 0; i < n; ++i) {
            long long time = (long long)(i + 1) * C;
            p.insert({time, v[i]});
            val_to_time[v[i]] = time;
        }

        std::sort(m.rbegin(), m.rend());

        for (int val : m) {
            long long current_time = val_to_time[val];
            int x = p.order_of_key({current_time, val}) + 1;

            long long y = 1 + (std::lower_bound(s.begin(), s.end(), val) - s.begin());

            std::cout << x << " " << y << std::endl;
            
            p.erase({current_time, val});
            
            long long new_time;
            if (y > p.size()) {
                if (p.empty()) {
                    new_time = C;
                } else {
                    new_time = p.rbegin()->first + C;
                }
            } else if (y == 1) {
                new_time = p.begin()->first - C;
            } else {
                 auto it_after = p.find_by_order(y - 1);
                 auto it_before = p.find_by_order(y - 2);
                 new_time = (it_before->first + it_after->first) / 2;
            }
            
            p.insert({new_time, val});
            val_to_time[val] = new_time;
        }
    }

    return 0;
}