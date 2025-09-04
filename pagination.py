# If you're using Flask-SQLAlchemy, you already have pagination
# If not, you can use this workaround:
from math import ceil


class Pagination:
    def __init__(self, query, page, per_page=50):
        self.query = query
        self.page = page
        self.per_page = per_page
        self.total = query.count()
    
    def min(self):
        return min(self.page * self.per_page, self.total)
    
    @property
    def items(self):
        return self.query.offset((self.page - 1) * self.per_page).limit(self.per_page).all()
    
    @property
    def pages(self):
        return ceil(self.total / self.per_page)
    
    def has_prev(self):
        return self.page > 1
    
    def has_next(self):
        return self.page < self.pages
    
    def prev_num(self):
        return self.page - 1
    
    def next_num(self):
        return self.page + 1
    
    def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

