#include <bits/stdc++.h>
using namespace std;

struct Bin {
    int W, H;
    bool allow_rotate;
};

struct Item {
    string type;
    int w, h, v, limit;
    long long area;
    double density;
};

struct Placement {
    string type;
    int x, y, rot;
};

// Segment tree for range max and range set
class SegTree {
    vector<int> tree, lazy;
    int n;

    void build(int node, int l, int r, const vector<int>& arr) {
        if (l == r) {
            tree[node] = arr[l];
            return;
        }
        int mid = (l + r) / 2;
        build(node*2, l, mid, arr);
        build(node*2+1, mid+1, r, arr);
        tree[node] = max(tree[node*2], tree[node*2+1]);
    }

    void push(int node, int l, int r) {
        if (lazy[node] != -1) {
            tree[node] = lazy[node];
            if (l != r) {
                lazy[node*2] = lazy[node];
                lazy[node*2+1] = lazy[node];
            }
            lazy[node] = -1;
        }
    }

    void update(int node, int l, int r, int ql, int qr, int val) {
        push(node, l, r);
        if (ql > r || qr < l) return;
        if (ql <= l && r <= qr) {
            lazy[node] = val;
            push(node, l, r);
            return;
        }
        int mid = (l + r) / 2;
        update(node*2, l, mid, ql, qr, val);
        update(node*2+1, mid+1, r, ql, qr, val);
        tree[node] = max(tree[node*2], tree[node*2+1]);
    }

    int query(int node, int l, int r, int ql, int qr) {
        push(node, l, r);
        if (ql > r || qr < l) return 0;
        if (ql <= l && r <= qr) return tree[node];
        int mid = (l + r) / 2;
        return max(query(node*2, l, mid, ql, qr),
                   query(node*2+1, mid+1, r, ql, qr));
    }

public:
    SegTree(int size, const vector<int>& arr) {
        n = size;
        tree.resize(4 * n);
        lazy.assign(4 * n, -1);
        build(1, 0, n-1, arr);
    }

    void setRange(int l, int r, int val) {
        update(1, 0, n-1, l, r, val);
    }

    int getMax(int l, int r) {
        return query(1, 0, n-1, l, r);
    }
};

// Find the best (x,y) for a rectangle of size (rw,rh) using bottom-left heuristic
pair<int,int> findBestPlacement(SegTree& st, int W, int H, int rw, int rh) {
    int best_x = -1;
    int best_y = INT_MAX;
    for (int x = 0; x <= W - rw; ++x) {
        int cur_h = st.getMax(x, x + rw - 1);
        if (cur_h + rh <= H && cur_h < best_y) {
            best_y = cur_h;
            best_x = x;
        }
    }
    if (best_x == -1) return {-1, -1};
    return {best_x, best_y};
}

// Pack items in the given order (Strategy A)
pair<long long, vector<Placement>> packByOrder(const Bin& bin, const vector<Item>& items,
                                               const vector<int>& order) {
    int W = bin.W;
    int H = bin.H;
    vector<int> height(W, 0);
    SegTree st(W, height);
    vector<Placement> placements;
    long long total_profit = 0;
    vector<int> remaining;
    for (const Item& it : items) remaining.push_back(it.limit);

    for (int idx : order) {
        const Item& it = items[idx];
        int placed = 0;
        while (placed < remaining[idx]) {
            pair<int,int> pos0 = findBestPlacement(st, W, H, it.w, it.h);
            pair<int,int> pos1 = {-1, -1};
            if (bin.allow_rotate && it.w != it.h) {
                pos1 = findBestPlacement(st, W, H, it.h, it.w);
            }
            int use_rot = 0;
            int x, y;
            if (pos0.first != -1 && pos1.first != -1) {
                if (pos0.second <= pos1.second) {
                    x = pos0.first; y = pos0.second; use_rot = 0;
                } else {
                    x = pos1.first; y = pos1.second; use_rot = 1;
                }
            } else if (pos0.first != -1) {
                x = pos0.first; y = pos0.second; use_rot = 0;
            } else if (pos1.first != -1) {
                x = pos1.first; y = pos1.second; use_rot = 1;
            } else {
                break; // cannot place more of this type
            }
            placements.push_back({it.type, x, y, use_rot});
            total_profit += it.v;
            int rw = (use_rot == 0 ? it.w : it.h);
            int rh = (use_rot == 0 ? it.h : it.w);
            st.setRange(x, x + rw - 1, y + rh);
            placed++;
        }
        remaining[idx] -= placed;
    }
    return {total_profit, placements};
}

// Greedy packing: at each step choose the item with highest profit that fits (Strategy B)
pair<long long, vector<Placement>> packGreedy(const Bin& bin, const vector<Item>& items) {
    int W = bin.W;
    int H = bin.H;
    vector<int> height(W, 0);
    SegTree st(W, height);
    vector<Placement> placements;
    long long total_profit = 0;
    vector<int> remaining;
    for (const Item& it : items) remaining.push_back(it.limit);

    while (true) {
        int best_profit = -1;
        int best_idx = -1;
        int best_rot = 0;
        int best_x = -1, best_y = -1;
        for (int i = 0; i < items.size(); ++i) {
            if (remaining[i] == 0) continue;
            const Item& it = items[i];
            // original orientation
            auto pos0 = findBestPlacement(st, W, H, it.w, it.h);
            if (pos0.first != -1 && it.v > best_profit) {
                best_profit = it.v;
                best_idx = i;
                best_rot = 0;
                best_x = pos0.first;
                best_y = pos0.second;
            }
            if (bin.allow_rotate && it.w != it.h) {
                auto pos1 = findBestPlacement(st, W, H, it.h, it.w);
                if (pos1.first != -1 && it.v > best_profit) {
                    best_profit = it.v;
                    best_idx = i;
                    best_rot = 1;
                    best_x = pos1.first;
                    best_y = pos1.second;
                }
            }
        }
        if (best_idx == -1) break;
        const Item& it = items[best_idx];
        placements.push_back({it.type, best_x, best_y, best_rot});
        total_profit += it.v;
        remaining[best_idx]--;
        int rw = (best_rot == 0 ? it.w : it.h);
        int rh = (best_rot == 0 ? it.h : it.w);
        st.setRange(best_x, best_x + rw - 1, best_y + rh);
    }
    return {total_profit, placements};
}

// Parse input JSON
void parseInput(const string& jsonStr, Bin& bin, vector<Item>& items) {
    // parse bin
    size_t pos = jsonStr.find("\"W\":");
    if (pos != string::npos) {
        pos += 4;
        while (pos < jsonStr.size() && (jsonStr[pos] == ' ' || jsonStr[pos] == '\t' || jsonStr[pos] == '\n')) pos++;
        bin.W = 0;
        while (pos < jsonStr.size() && isdigit(jsonStr[pos])) {
            bin.W = bin.W * 10 + (jsonStr[pos] - '0');
            pos++;
        }
    }
    pos = jsonStr.find("\"H\":");
    if (pos != string::npos) {
        pos += 4;
        while (pos < jsonStr.size() && (jsonStr[pos] == ' ' || jsonStr[pos] == '\t' || jsonStr[pos] == '\n')) pos++;
        bin.H = 0;
        while (pos < jsonStr.size() && isdigit(jsonStr[pos])) {
            bin.H = bin.H * 10 + (jsonStr[pos] - '0');
            pos++;
        }
    }
    pos = jsonStr.find("\"allow_rotate\":");
    if (pos != string::npos) {
        pos += 15;
        while (pos < jsonStr.size() && (jsonStr[pos] == ' ' || jsonStr[pos] == '\t' || jsonStr[pos] == '\n')) pos++;
        bin.allow_rotate = (jsonStr.substr(pos, 4) == "true");
    }

    // parse items array
    pos = jsonStr.find("\"items\":[");
    if (pos == string::npos) return;
    pos += 9; // length of "\"items\":["
    size_t end_pos = pos;
    int bracket = 1;
    while (end_pos < jsonStr.size() && bracket > 0) {
        if (jsonStr[end_pos] == '[') bracket++;
        else if (jsonStr[end_pos] == ']') bracket--;
        end_pos++;
    }
    string arr_str = jsonStr.substr(pos, end_pos - pos - 1);
    size_t obj_start = 0;
    while (obj_start < arr_str.size()) {
        size_t open = arr_str.find('{', obj_start);
        if (open == string::npos) break;
        size_t close = arr_str.find('}', open);
        if (close == string::npos) break;
        string obj = arr_str.substr(open, close - open + 1);
        Item item;
        // type
        size_t tpos = obj.find("\"type\":");
        if (tpos != string::npos) {
            tpos += 7;
            while (tpos < obj.size() && (obj[tpos] == ' ' || obj[tpos] == '\t' || obj[tpos] == '\n')) tpos++;
            if (obj[tpos] == '"') {
                size_t end_quote = obj.find('"', tpos + 1);
                item.type = obj.substr(tpos + 1, end_quote - tpos - 1);
            }
        }
        // w
        tpos = obj.find("\"w\":");
        if (tpos != string::npos) {
            tpos += 4;
            while (tpos < obj.size() && (obj[tpos] == ' ' || obj[tpos] == '\t' || obj[tpos] == '\n')) tpos++;
            item.w = 0;
            while (tpos < obj.size() && isdigit(obj[tpos])) {
                item.w = item.w * 10 + (obj[tpos] - '0');
                tpos++;
            }
        }
        // h
        tpos = obj.find("\"h\":");
        if (tpos != string::npos) {
            tpos += 4;
            while (tpos < obj.size() && (obj[tpos] == ' ' || obj[tpos] == '\t' || obj[tpos] == '\n')) tpos++;
            item.h = 0;
            while (tpos < obj.size() && isdigit(obj[tpos])) {
                item.h = item.h * 10 + (obj[tpos] - '0');
                tpos++;
            }
        }
        // v
        tpos = obj.find("\"v\":");
        if (tpos != string::npos) {
            tpos += 4;
            while (tpos < obj.size() && (obj[tpos] == ' ' || obj[tpos] == '\t' || obj[tpos] == '\n')) tpos++;
            item.v = 0;
            while (tpos < obj.size() && isdigit(obj[tpos])) {
                item.v = item.v * 10 + (obj[tpos] - '0');
                tpos++;
            }
        }
        // limit
        tpos = obj.find("\"limit\":");
        if (tpos != string::npos) {
            tpos += 8;
            while (tpos < obj.size() && (obj[tpos] == ' ' || obj[tpos] == '\t' || obj[tpos] == '\n')) tpos++;
            item.limit = 0;
            while (tpos < obj.size() && isdigit(obj[tpos])) {
                item.limit = item.limit * 10 + (obj[tpos] - '0');
                tpos++;
            }
        }
        item.area = (long long)item.w * item.h;
        item.density = (item.area > 0) ? (double)item.v / item.area : 0.0;
        items.push_back(item);
        obj_start = close + 1;
        while (obj_start < arr_str.size() && (arr_str[obj_start] == ' ' || arr_str[obj_start] == ',' || arr_str[obj_start] == '\n'))
            obj_start++;
    }
}

int main() {
    // Read entire input
    string jsonStr;
    char ch;
    while (cin.get(ch)) jsonStr += ch;

    Bin bin;
    vector<Item> items;
    parseInput(jsonStr, bin, items);
    int n = items.size();

    // Precompute orders to try
    vector<vector<int>> orders;

    // 1. by value density descending
    vector<int> order1(n);
    iota(order1.begin(), order1.end(), 0);
    sort(order1.begin(), order1.end(), [&](int a, int b) {
        return items[a].density > items[b].density;
    });
    orders.push_back(order1);

    // 2. by profit descending
    vector<int> order2(n);
    iota(order2.begin(), order2.end(), 0);
    sort(order2.begin(), order2.end(), [&](int a, int b) {
        return items[a].v > items[b].v;
    });
    orders.push_back(order2);

    // 3. by area descending
    vector<int> order3(n);
    iota(order3.begin(), order3.end(), 0);
    sort(order3.begin(), order3.end(), [&](int a, int b) {
        return items[a].area > items[b].area;
    });
    orders.push_back(order3);

    // 4. by width descending
    vector<int> order4(n);
    iota(order4.begin(), order4.end(), 0);
    sort(order4.begin(), order4.end(), [&](int a, int b) {
        return items[a].w > items[b].w;
    });
    orders.push_back(order4);

    // 5. by height descending
    vector<int> order5(n);
    iota(order5.begin(), order5.end(), 0);
    sort(order5.begin(), order5.end(), [&](int a, int b) {
        return items[a].h > items[b].h;
    });
    orders.push_back(order5);

    // 6. by min(w,h) descending
    vector<int> order6(n);
    iota(order6.begin(), order6.end(), 0);
    sort(order6.begin(), order6.end(), [&](int a, int b) {
        return min(items[a].w, items[a].h) > min(items[b].w, items[b].h);
    });
    orders.push_back(order6);

    // 7. by max(w,h) descending
    vector<int> order7(n);
    iota(order7.begin(), order7.end(), 0);
    sort(order7.begin(), order7.end(), [&](int a, int b) {
        return max(items[a].w, items[a].h) > max(items[b].w, items[b].h);
    });
    orders.push_back(order7);

    // 8-12. random orders
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    for (int i = 0; i < 5; ++i) {
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        orders.push_back(order);
    }

    // Try all orders with Strategy A and keep the best
    long long best_profit = 0;
    vector<Placement> best_placements;

    for (const auto& order : orders) {
        auto [profit, placements] = packByOrder(bin, items, order);
        if (profit > best_profit) {
            best_profit = profit;
            best_placements = placements;
        }
    }

    // Also try greedy strategy (Strategy B)
    auto [profit_greedy, placements_greedy] = packGreedy(bin, items);
    if (profit_greedy > best_profit) {
        best_profit = profit_greedy;
        best_placements = placements_greedy;
    }

    // Output JSON
    cout << "{\"placements\":[";
    for (size_t i = 0; i < best_placements.size(); ++i) {
        if (i > 0) cout << ",";
        cout << "{\"type\":\"" << best_placements[i].type
             << "\",\"x\":" << best_placements[i].x
             << ",\"y\":" << best_placements[i].y
             << ",\"rot\":" << best_placements[i].rot << "}";
    }
    cout << "]}" << endl;

    return 0;
}