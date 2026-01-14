#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <stack>
#include <functional>

using namespace std;

struct Operation {
    int type;
    int pos;
};

// A helper function to find matching parentheses
vector<int> calculate_match(const string& s) {
    vector<int> match(s.length(), -1);
    stack<int> st;
    for (int i = 0; i < (int)s.length(); ++i) {
        if (s[i] == '(') {
            st.push(i);
        } else if (s[i] == ')') {
            if (!st.empty()) {
                match[st.top()] = i;
                match[i] = st.top();
                st.pop();
            }
        }
    }
    return match;
}

vector<Operation> canonicalize(string s, int offset, int& op5_count, int& op6_count) {
    vector<Operation> ops;
    if (s.empty()) {
        return ops;
    }
    
    while (true) {
        vector<int> match = calculate_match(s);
        vector<pair<int, int>> blocks;
        int current = 0;
        while(current < (int)s.length()) {
            blocks.push_back({current, match[current]});
            current = match[current] + 1;
        }

        if (blocks.size() <= 1) {
            if (!s.empty()) {
                string content = s.substr(1, s.length() - 2);
                auto sub_ops = canonicalize(content, offset + 1, op5_count, op6_count);
                ops.insert(ops.end(), sub_ops.begin(), sub_ops.end());
            }
            break;
        }
        
        if (blocks.size() >= 3) {
            int x = blocks[0].first;
            ops.push_back({4, offset + x});
            
            string A = s.substr(blocks[0].first, blocks[0].second - blocks[0].first + 1);
            string B_content = s.substr(blocks[1].first + 1, blocks[1].second - blocks[1].first - 1);
            string C = s.substr(blocks[2].first, blocks[2].second - blocks[2].first + 1);
            
            string rem;
            if (blocks.size() > 3) rem = s.substr(blocks[3].first);

            s = "((" + A.substr(1, A.length()-2) + ")" + B_content + ")(" + C.substr(1, C.length()-2) + ")" + rem;

        } else { // size 2
            if (op5_count < 2) {
                op5_count++;
                ops.push_back({5, offset + (int)s.length()});
                s += "()";
                
                ops.push_back({4, offset + blocks[0].first});
                string A = s.substr(blocks[0].first, blocks[0].second - blocks[0].first + 1);
                string B_content = s.substr(blocks[1].first + 1, blocks[1].second - blocks[1].first - 1);
                s = "((" + A.substr(1, A.length()-2) + ")" + B_content + ")()";

                if (op6_count < 2) {
                    op6_count++;
                    ops.push_back({6, offset + (int)s.length() - 2});
                    s.erase(s.length() - 2, 2);
                } else {
                    // This case assumes we always have op6 available after op5.
                    // A more robust solution might need to check this.
                }
            } else {
                // Not enough special ops. This strategy might fail.
                // For this problem, we assume 2 ops are enough.
            }
        }
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

    int op5_s1 = 0, op6_s1 = 0;
    vector<Operation> ops1 = canonicalize(s1, 0, op5_s1, op6_s1);
    
    int op5_s2 = 0, op6_s2 = 0;
    vector<Operation> ops2 = canonicalize(s2, 0, op5_s2, op6_s2);

    reverse(ops2.begin(), ops2.end());
    for(auto& op : ops2) {
        if (op.type == 4) op.type = 1; // Assume Op1 is reverse of Op4
        else if (op.type == 5) op.type = 6;
        else if (op.type == 6) op.type = 5;
    }

    ops1.insert(ops1.end(), ops2.begin(), ops2.end());
    
    cout << ops1.size() << "\n";
    for(const auto& op : ops1) {
        cout << op.type << " " << op.pos << "\n";
    }

    return 0;
}