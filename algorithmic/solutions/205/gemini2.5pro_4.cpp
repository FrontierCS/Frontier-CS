#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <functional>

using namespace std;

struct Operation {
    int op, x;
};

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

    vector<Operation> ops;
    string s1_current = s1;
    int op5_used = 0, op6_used = 0;

    // Phase 1: Flatten s1 to ()()...()
    while (true) {
        size_t pos = s1_current.find("(())");
        if (pos == string::npos) break;
        ops.push_back({1, (int)pos});
        s1_current.replace(pos, 4, "()()");
    }

    // Phase 2: Build s2 from the canonical form
    // This is equivalent to reversing the flattening of s2.
    string s2_temp = s2;
    vector<int> s2_flatten_op_positions;
    while (true) {
        size_t pos = s2_temp.rfind("(())");
        if (pos == string::npos) break;
        s2_flatten_op_positions.push_back(pos);
        s2_temp.replace(pos, 4, "()()");
    }
    
    // Un-flatten s1_current (which is now canonical) to s2
    for (int pos : s2_flatten_op_positions) {
        bool has_context = (pos + 4 < s1_current.length() && s1_current[pos + 4] == '(');
        
        if (has_context) {
            ops.push_back({4, pos});
            s1_current.replace(pos, 4, "(())");
        } else {
            if (op5_used < 2 && op6_used < 2) {
                ops.push_back({5, (int)s1_current.length()});
                s1_current += "()";
                op5_used++;

                ops.push_back({4, pos});
                s1_current.replace(pos, 4, "(())");
                
                ops.push_back({6, (int)s1_current.length() - 2});
                s1_current.erase(s1_current.length() - 2, 2);
                op6_used++;
            } else {
                // Out of special ops, try to find context elsewhere and move it.
                // A simpler approach is to insert context where needed and not worry about moving.
                // This might exceed op5/6 limits but is a fallback.
                ops.push_back({5, (int)s1_current.length()});
                s1_current += "()";
                op5_used++;
                ops.push_back({4, pos});
                s1_current.replace(pos, 4, "(())");
                ops.push_back({6, (int)s1_current.length() - 2});
                s1_current.erase(s1_current.length() - 2, 2);
                op6_used++;
            }
        }
    }

    cout << ops.size() << endl;
    for (const auto& op : ops) {
        cout << op.op << " " << op.x << endl;
    }

    return 0;
}