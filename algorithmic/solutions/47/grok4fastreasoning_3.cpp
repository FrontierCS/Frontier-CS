#include <bits/stdc++.h>
using namespace std;

struct Item {
    string type;
    int w, h, v, limit;
    int used = 0;
};

struct Placement {
    string type;
    int x, y, rot;
};

class SegTree {
private:
    int n;
    vector<int> tree, lazy;
    vector<bool> has_lazy;
    void build(int node, int start, int end) {
        if (start == end) {
            tree[node] = 0;
            return;
        }
        int mid = (start + end) / 2;
        build(2 * node, start, mid);
        build(2 * node + 1, mid + 1, end);
        tree[node] = max(tree[2 * node], tree[2 * node + 1]);
    }
    void propagate(int node, int start, int end) {
        if (has_lazy[node]) {
            tree[node] = lazy[node];
            if (start != end) {
                lazy[2 * node] = lazy[node];
                has_lazy[2 * node] = true;
                lazy[2 * node + 1] = lazy[node];
                has_lazy[2 * node + 1] = true;
            }
            has_lazy[node] = false;
        }
    }
    void update_range(int node, int start, int end, int l, int r, int val) {
        propagate(node, start, end);
        if (start > end || start > r || end < l) return;
        if (start >= l && end <= r) {
            lazy[node] = val;
            has_lazy[node] = true;
            propagate(node, start, end);
            return;
        }
        int mid = (start + end) / 2;
        update_range(2 * node, start, mid, l, r, val);
        update_range(2 * node + 1, mid + 1, end, l, r, val);
        tree[node] = max(tree[2 * node], tree[2 * node + 1]);
    }
    int query_max(int node, int start, int end, int l, int r) {
        propagate(node, start, end);
        if (start > end || start > r || end < l) return INT_MIN / 2;
        if (start >= l && end <= r) {
            return tree[node];
        }
        int mid = (start + end) / 2;
        int p1 = query_max(2 * node, start, mid, l, r);
        int p2 = query_max(2 * node + 1, mid + 1, end, l, r);
        return max(p1, p2);
    }
public:
    SegTree(int _n) : n(_n), tree(4 * _n), lazy(4 * _n), has_lazy(4 * _n, false) {
        build(1, 0, n - 1);
    }
    void update(int l, int r, int val) {
        update_range(1, 0, n - 1, l, r, val);
    }
    int query(int l, int r) {
        return query_max(1, 0, n - 1, l, r);
    }
};

string parse_string(const string& s, const string& key) {
    size_t p = s.find("\"" + key + "\":");
    if (p == string::npos) {
        cerr << "Parse error: no key " << key << endl;
        exit(1);
    }
    p += key.length() + 3;
    if (p >= s.size() || s[p] != '"') {
        cerr << "Parse error: string expected" << endl;
        exit(1);
    }
    p++;
    size_t q = s.find("\"", p);
    if (q == string::npos) {
        cerr << "Parse error: unclosed string" << endl;
        exit(1);
    }
    return s.substr(p, q - p);
}

int parse_int(const string& s, const string& key) {
    size_t p = s.find("\"" + key + "\":");
    if (p == string::npos) {
        cerr << "Parse error: no key " << key << endl;
        exit(1);
    }
    p += key.length() + 3;
    bool neg = false;
    if (p < s.size() && s[p] == '-') {
        neg = true;
        p++;
    }
    int num = 0;
    while (p < s.size() && isdigit(s[p])) {
        num = num * 10 + (s[p] - '0');
        p++;
    }
    return neg ? -num : num;
}

bool parse_bool(const string& s, const string& key) {
    size_t p = s.find("\"" + key + "\":");
    if (p == string::npos) {
        cerr << "Parse error: no key " << key << endl;
        exit(1);
    }
    p += key.length() + 3;
    if (p + 4 <= s.size() && s.substr(p, 4) == "true") return true;
    if (p + 5 <= s.size() && s.substr(p, 5) == "false") return false;
    cerr << "Parse error: bool expected" << endl;
    exit(1);
    return false;
}

int main() {
    string input_str((istreambuf_iterator<char>(cin)), istreambuf_iterator<char>());
    string json;
    for (char c : input_str) {
        if (!isspace(c)) json += c;
    }
    if (json.empty() || json[0] != '{' || json.back() != '}') {
        cerr << "Invalid JSON" << endl;
        return 1;
    }

    // Parse bin
    size_t bin_pos = json.find("\"bin\":");
    if (bin_pos == string::npos) {
        cerr << "No bin" << endl;
        return 1;
    }
    bin_pos += 6;
    size_t bin_start = json.find("{", bin_pos);
    if (bin_start == string::npos) {
        cerr << "No bin object" << endl;
        return 1;
    }
    size_t bin_end = json.find("}", bin_start);
    if (bin_end == string::npos) {
        cerr << "Invalid bin" << endl;
        return 1;
    }
    string bin_str = json.substr(bin_start, bin_end - bin_start + 1);
    int W = parse_int(bin_str, "W");
    int H = parse_int(bin_str, "H");
    bool allow_rot = parse_bool(bin_str, "allow_rotate");

    // Parse items
    size_t items_pos = json.find("\"items\":", bin_end);
    if (items_pos == string::npos) {
        cerr << "No items" << endl;
        return 1;
    }
    items_pos += 8;
    size_t arr_start = json.find("[", items_pos);
    if (arr_start == string::npos) {
        cerr << "No items array" << endl;
        return 1;
    }
    size_t arr_end = json.find("]", arr_start + 1);
    if (arr_end == string::npos) {
        cerr << "Invalid items array" << endl;
        return 1;
    }
    string items_inside = json.substr(arr_start + 1, arr_end - arr_start - 1);

    vector<Item> items;
    size_t cur = 0;
    while (cur < items_inside.size()) {
        size_t obj_start = items_inside.find("{", cur);
        if (obj_start == string::npos) break;
        size_t obj_end = items_inside.find("}", obj_start + 1);
        if (obj_end == string::npos) {
            cerr << "Invalid item object" << endl;
            return 1;
        }
        string obj = items_inside.substr(obj_start, obj_end - obj_start + 1);
        Item it;
        it.type = parse_string(obj, "type");
        it.w = parse_int(obj, "w");
        it.h = parse_int(obj, "h");
        it.v = parse_int(obj, "v");
        it.limit = parse_int(obj, "limit");
        items.push_back(it);
        cur = obj_end + 1;
    }

    // Sort by density descending
    sort(items.begin(), items.end(), [](const Item& a, const Item& b) {
        double da = (double)a.v / (a.w * a.h);
        double db = (double)b.v / (b.w * b.h);
        return da > db || (da == db && a.type < b.type);
    });

    SegTree st(W);
    vector<Placement> placements;

    for (size_t i = 0; i < items.size(); ++i) {
        Item& it = items[i];
        int remaining = it.limit - it.used;
        for (int c = 0; c < remaining; ++c) {
            int best_y = INT_MAX;
            int best_x = INT_MAX;
            int best_r = 2;  // invalid
            vector<int> rots = allow_rot ? vector<int>{0, 1} : vector<int>{0};

            for (int r : rots) {
                int ww = (r == 0 ? it.w : it.h);
                int hh = (r == 0 ? it.h : it.w);
                if (ww > W || hh > H) continue;
                int this_best_y = INT_MAX;
                int this_best_x = INT_MAX;
                for (int sx = 0; sx <= W - ww; ++sx) {
                    int m = st.query(sx, sx + ww - 1);
                    int py = m;
                    if (py + hh <= H) {
                        if (py < this_best_y || (py == this_best_y && sx < this_best_x)) {
                            this_best_y = py;
                            this_best_x = sx;
                        }
                    }
                }
                if (this_best_y != INT_MAX) {
                    bool better = (this_best_y < best_y) ||
                                  (this_best_y == best_y && this_best_x < best_x) ||
                                  (this_best_y == best_y && this_best_x == best_x && r < best_r);
                    if (better) {
                        best_y = this_best_y;
                        best_x = this_best_x;
                        best_r = r;
                    }
                }
            }
            if (best_y == INT_MAX) break;
            int ww = (best_r == 0 ? it.w : it.h);
            int hh = (best_r == 0 ? it.h : it.w);
            st.update(best_x, best_x + ww - 1, best_y + hh);
            placements.push_back({it.type, best_x, best_y, best_r});
            ++it.used;
        }
    }

    // Output
    cout << "{\"placements\":[";
    for (size_t j = 0; j < placements.size(); ++j) {
        if (j > 0) cout << ",";
        const auto& p = placements[j];
        cout << "{\"type\":\"" << p.type << "\",\"x\":" << p.x << ",\"y\":" << p.y << ",\"rot\":" << p.rot << "}";
    }
    cout << "]}";
    cout << endl;
    return 0;
}