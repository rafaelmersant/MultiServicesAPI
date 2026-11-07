"""XMLDSig verification with stable inclusive-C14N namespace context."""

from lxml import etree
from signxml import XMLVerifier
from signxml.algorithms import CanonicalizationMethod


class ReceiverXMLVerifier(XMLVerifier):
    def _c14n(self, nodes, algorithm, inclusive_ns_prefixes=None):
        def stable(node):
            if (algorithm == CanonicalizationMethod.CANONICAL_XML_1_0
                    and node.tag == "{http://www.w3.org/2000/09/xmldsig#}SignedInfo"
                    and not any(
                        key.startswith("{http://www.w3.org/XML/1998/namespace}")
                        for ancestor in node.iterancestors() for key in ancestor.attrib
                    )):
                # libxml2 can insert spurious xmlns="" when canonicalizing
                # this subtree in-place. A namespace-preserving round trip
                # retains in-scope declarations, text and explicit undeclarations.
                # Do not strip namespaces, whitespace or signature checks.
                return etree.fromstring(
                    etree.tostring(node, with_tail=False),
                    etree.XMLParser(resolve_entities=False, no_network=True, remove_blank_text=False),
                )
            return node

        stable_nodes = [stable(node) for node in nodes] if isinstance(nodes, list) else stable(nodes)
        return super()._c14n(stable_nodes, algorithm, inclusive_ns_prefixes)
