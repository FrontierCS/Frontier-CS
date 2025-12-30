#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <map>
#include <algorithm>

using namespace std;

int n;
map<string, int> query_cache;

string set_to_string(const vector<int>& s) {
    string res(n, '0');
    for (int v : s) {
        res[v - 1] = '1';
    }
    return res;
}

string multi_set_to_string_union(const vector<vector<int>>& sets, int start, int end) {
    string res(n, '0');
    for (int i = start; i <= end; ++i) {
        for (int v : sets[i]) {
            res[v - 1] = '1';
        }
    }
    return res;
}

int do_query(const string& s) {
    if (s.find('1') == string::npos) {
        return 0;
    }
    if (query_cache.count(s)) {
        return query_cache[s];
    }
    cout << "? " << s << endl;
    int result;
    cin >> result;
    if (result == -1) exit(0); // Error guard
    return query_cache[s] = result;
}

vector<vector<int>> components;
vector<int> main_component;

int find_connection_recursive(int start, int end) {
    if (start > end) {
        return -1;
    }

    string main_comp_str = set_to_string(main_component);
    string sub_comps_union_str = multi_set_to_string_union(components, start, end);
    
    string total_union_str = main_comp_str;
    for(size_t i = 0; i < sub_comps_union_str.length(); ++i) {
        if(sub_comps_union_str[i] == '1') {
            total_union_str[i] = '1';
        }
    }

    int q_main = do_query(main_comp_str);
    int q_sub = do_query(sub_comps_union_str);
    int q_total_union = do_query(total_union_str);

    if (q_main + q_sub <= q_total_union) {
        return -1;
    }
    
    if (start == end) {
        return start;
    }
    
    int mid = start + (end - start) / 2;
    int res = find_connection_recursive(start, mid);
    if (res != -1) {
        return res;
    }
    return find_connection_recursive(mid + 1, end);
}

void solve() {
    cin >> n;
    query_cache.clear();

    if (n == 1) {
        cout << "! 1" << endl;
        return;
    }

    main_component = {1};
    components.clear();
    for (int i = 2; i <= n; ++i) {
        components.push_back({i});
    }

    while (main_component.size() < n && !components.empty()) {
        int idx_to_merge = find_connection_recursive(0, components.size() - 1);
        
        if (idx_to_merge == -1) {
            cout << "! 0" << endl;
            return;
        }

        main_component.insert(main_component.end(), components[idx_to_merge].begin(), components[idx_to_merge].end());
        swap(components[idx_to_merge], components.back());
        components.pop_back();
    }
    
    if (main_component.size() == n) {
        cout << "! 1" << endl;
    } else {
        cout << "! 0" << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}