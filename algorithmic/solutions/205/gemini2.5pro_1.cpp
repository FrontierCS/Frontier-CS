#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <functional>

using namespace std;

// Maps for keeping track of parenthesis pairs and their IDs
vector<int> match;
vector<int> open_pos_to_id;
vector<int> id_to_open_pos;
int N_current;

// Operation to be recorded
struct Operation {
    int type;
    int pos;
};

// Computes matching parentheses and assigns IDs to each pair
void compute_metadata(const string& s) {
    int len = s.length();
    N_current = len / 2;
    if (N_current == 0) return;
    match.assign(len, -1);
    open_pos_to_id.assign(len, -1);
    id_to_open_pos.assign(N_current, -1);
    vector<int> st;
    int id_counter = 0;
    for (int i = 0; i < len; ++i) {
        if (s[i] == '(') {
            st.push_back(i);
            open_pos_to_id[i] = id_counter;
            id_to_open_pos[id_counter] = i;
            id_counter++;
        } else {
            int open_pos = st.back();
            st.pop_back();
            match[open_pos] = i;
            match[i] = open_pos;
        }
    }
}

// Builds the parent-child relationships from a parenthesis string
void get_children(int u_id, const string& s, vector<int>& children) {
    children.clear();
    int u_pos = id_to_open_pos[u_id];
    int current_pos = u_pos + 1;
    while (current_pos < match[u_pos]) {
        children.push_back(open_pos_to_id[current_pos]);
        current_pos = match[current_pos] + 1;
    }
}


// Transforms a string to a canonical left-deep form, e.g., (((...)))
vector<Operation> to_canonical(string& s) {
    vector<Operation> ops;
    int n = s.length() / 2;
    if (n == 0) return ops;

    vector<int> p_order;
    vector<bool> visited(n, false);
    
    function<void(int)> post_order_dfs = 
        [&](int u_id) {
        visited[u_id] = true;
        vector<int> children;
        get_children(u_id, s, children);
        for (int v_id : children) {
            if (!visited[v_id]) {
                post_order_dfs(v_id);
            }
        }
        p_order.push_back(u_id);
    };
    
    compute_metadata(s);
    int current_pos = 0;
    while(current_pos < s.length()) {
        post_order_dfs(open_pos_to_id[current_pos]);
        current_pos = match[current_pos] + 1;
    }

    for (int id : p_order) {
        while (true) {
            compute_metadata(s);
            vector<int> children;
            get_children(id, s, children);

            if (children.size() <= 1) break;

            int c1_id = children[0];
            int c1_pos = id_to_open_pos[c1_id];

            ops.push_back({4, c1_pos});
            
            int c1_end = match[c1_pos];
            int c2_pos = c1_end + 1;
            int c2_end = match[c2_pos];
            
            string s_c1_content = s.substr(c1_pos + 1, c1_end - c1_pos - 1);
            string s_c2_content = s.substr(c2_pos + 1, c2_end - c2_pos - 1);
            
            string merged_content = "(" + s_c1_content + ")" + s_c2_content;
            string merged = "(" + merged_content + ")";
            
            s = s.substr(0, c1_pos) + merged + s.substr(c2_end + 1);
        }
    }

    // Merge roots
    while (true) {
        compute_metadata(s);
        vector<int> roots;
        current_pos = 0;
        while (current_pos < s.length()) {
            roots.push_back(open_pos_to_id[current_pos]);
            current_pos = match[current_pos] + 1;
        }
        
        if (roots.size() <= 1) break;
        
        ops.push_back({4, 0});
        
        int r1_pos = 0;
        int r1_end = match[r1_pos];
        int r2_pos = r1_end + 1;
        int r2_end = match[r2_pos];

        string s_r1_content = s.substr(r1_pos + 1, r1_end - r1_pos - 1);
        string s_r2_content = s.substr(r2_pos + 1, r2_end - r2_pos - 1);
        
        string merged_content = "(" + s_r1_content + ")" + s_r2_content;
        string merged = "(" + merged_content + ")";

        s = merged + s.substr(r2_end + 1);
    }

    return ops;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;
    string s1, s2;
    cin >> s1 >> s2;

    if (s1 == s2) {
        cout << 0 << endl;
        return 0;
    }

    string s1_copy = s1;
    vector<Operation> ops1 = to_canonical(s1_copy);

    string s2_copy = s2;
    vector<Operation> ops2 = to_canonical(s2_copy);

    reverse(ops2.begin(), ops2.end());
    
    string s_temp = s1_copy;
    for(auto& op : ops2) {
        compute_metadata(s_temp);
        int pos = op.pos;
        
        string left_part = s_temp.substr(0, pos);
        string node_str = s_temp.substr(pos, match[pos] - pos + 1);
        string right_part = s_temp.substr(match[pos] + 1);
        
        string content = node_str.substr(1, node_str.length() - 2);
        
        compute_metadata(content);
        
        int c1_pos_in_content = 0;
        int c1_end_in_content = match[c1_pos_in_content];
        
        string c1 = content.substr(c1_pos_in_content, c1_end_in_content + 1);
        string c1_content = c1.substr(1, c1.length() - 2);
        
        string c2_content = content.substr(c1_end_in_content + 1);
        
        string split_c1 = "(" + c1_content + ")";
        string split_c2 = "(" + c2_content + ")";
        
        s_temp = left_part + split_c1 + split_c2 + right_part;
        op.type = 1; 
    }

    vector<Operation> all_ops = ops1;
    all_ops.insert(all_ops.end(), ops2.begin(), ops2.end());

    cout << all_ops.size() << endl;
    for (const auto& op : all_ops) {
        cout << op.type << " " << op.pos << endl;
    }

    return 0;
}