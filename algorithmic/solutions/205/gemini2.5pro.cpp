#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <list>

using namespace std;

struct Operation {
    int type;
    int pos;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;
    string s1, s2;
    cin >> s1 >> s2;

    vector<Operation> ops;

    for (int d = 0; d <= 2; ++d) {
        string s_cur = s1;
        vector<Operation> current_ops;

        for (int i = 0; i < d; ++i) {
            current_ops.push_back({5, (int)s_cur.length()});
            s_cur += "()";
        }
        
        string s_target = s2;
        for (int i = 0; i < d; ++i) {
            s_target += "()";
        }

        string temp_s = s_cur;
        vector<Operation> transform_ops;

        while (true) {
            if (temp_s.length() == 0) break;

            vector<int> match(temp_s.length());
            vector<int> st;
            for (int i = 0; i < temp_s.length(); ++i) {
                if (temp_s[i] == '(') {
                    st.push_back(i);
                } else {
                    match[st.back()] = i;
                    match[i] = st.back();
                    st.pop_back();
                }
            }

            vector<pair<int, int>> top_level;
            int current_pos = 0;
            while (current_pos < temp_s.length()) {
                top_level.push_back({current_pos, match[current_pos] - current_pos + 1});
                current_pos = match[current_pos] + 1;
            }

            if (top_level.size() <= 1) break;

            int op_pos = top_level[0].first;
            transform_ops.push_back({4, op_pos});

            int pos_A = top_level[0].first;
            int len_A = top_level[0].second;
            int pos_B = top_level[1].first;
            int len_B = top_level[1].second;
            
            string A_content = temp_s.substr(pos_A + 1, len_A - 2);
            string B_content = temp_s.substr(pos_B + 1, len_B - 2);

            string merged = "((" + A_content + ")" + B_content + ")";
            temp_s.replace(pos_A, len_A + len_B, merged);
        }

        if (temp_s == s_target) {
            ops = current_ops;
            ops.insert(ops.end(), transform_ops.begin(), transform_ops.end());
            for (int i = 0; i < d; ++i) {
                ops.push_back({6, (int)s2.length() + i * 2});
            }
            goto end_loops;
        }
    }

end_loops:;

    cout << ops.size() << "\n";
    for (const auto& op : ops) {
        cout << op.type << " " << op.pos << "\n";
    }

    return 0;
}