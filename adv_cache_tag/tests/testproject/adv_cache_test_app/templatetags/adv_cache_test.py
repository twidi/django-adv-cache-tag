from django import template

from adv_cache_tag.tag import CacheTag, Node

register = template.Library()


class TestNode(Node):
    def __init__(self, nodename, nodelist, expire_time, multiplicator, fragment_name, vary_on):
        """ Save the multiplicator variable in the node (not resolved yet) """
        super(TestNode, self).__init__(nodename, nodelist, expire_time, fragment_name, vary_on)
        self.multiplicator = multiplicator


class TestCacheTag(CacheTag):
    class Meta(CacheTag.Meta):
        compress_spaces = True

    Node = TestNode

    @classmethod
    def get_template_node_arguments(cls, tokens):
        """ Check validity of tokens and return them as ready to be passed to the Node class """
        if len(tokens) < 4:
            raise template.TemplateSyntaxError(
                "'%r' tag requires at least 3 arguments." % tokens[0])
        return tokens[1], tokens[2], tokens[3], tokens[4:]

    def prepare_params(self):
        """ Resolve the multiplicator variable to it's real content """
        self.multiplicator = int(template.Variable(self.node.multiplicator).resolve(self.context))
        super(TestCacheTag, self).prepare_params()

    def get_expire_time(self):
        """Update the expiry time with the multiplicator."""
        expiry_time = super(TestCacheTag, self).get_expire_time()
        return self.multiplicator * expiry_time

TestCacheTag.register(register, 'cache_test', 'nocache_test')


class FailingCacheSetCacheTag(CacheTag):
    def cache_set(self, to_cache):
        raise ValueError('boom set')

FailingCacheSetCacheTag.register(register, 'cache_set_fail')


class FailingCacheGetCacheTag(CacheTag):
    def cache_get(self):
        raise ValueError('boom get')

FailingCacheGetCacheTag.register(register, 'cache_get_fail')
